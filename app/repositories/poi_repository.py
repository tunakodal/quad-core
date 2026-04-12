"""
POI data source and repository implementations.

İki strateji:
  JsonDataSource / PoiRepository      — JSON dosyasından okur (geliştirme / fallback)
  PostgresPoiRepository               — Supabase Data API üzerinden okur (production)

DB ↔ domain model farkları (PostgresPoiRepository tarafından çözülür):
  pois.id              INTEGER  → domain Poi.id: str   (str() ile dönüştürülür)
  pois.categories      TEXT[]   → domain Poi.category: str  (main_category_1 kullanılır)
  estimated_visit_duration       → tabloda yok, sabit 60 dk kullanılır
"""
from __future__ import annotations

import json
from pathlib import Path

from app.models.geo import GeoPoint
from app.models.poi import Poi
from app.repositories.interfaces import AbstractDataSource, AbstractPoiRepository


# ── JSON / geliştirme implementasyonu ────────────────────────────

class JsonDataSource(AbstractDataSource):
    """
    POI kayıtlarını disk üzerindeki JSON dosyasından yükler.

    Geliştirme ortamında ve Supabase bağlantısı olmadığında fallback olarak kullanılır.
    Dosya yoksa sessizce boş liste döner; uygulama başlamaya devam eder.
    """

    def __init__(self, json_path: str):
        self._pois: list[Poi] = []
        self._index: dict[str, Poi] = {}
        self._load(json_path)

    def _load(self, json_path: str) -> None:
        """JSON dosyasını okur ve belleğe alır."""
        path = Path(json_path)
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for item in raw:
            poi = Poi(
                id=item["id"],
                name=item["name"],
                category=item["category"],
                city=item["city"],
                location=GeoPoint(
                    latitude=item["location"]["latitude"],
                    longitude=item["location"]["longitude"],
                ),
                estimated_visit_duration=item["estimated_visit_duration"],
            )
            self._pois.append(poi)
            self._index[poi.id] = poi

    def load_all_pois(self) -> list[Poi]:
        """Yüklü tüm POI'ları döner."""
        return list(self._pois)

    def load_by_id(self, poi_id: str) -> Poi | None:
        """Verilen ID'ye sahip POI'yı döner; bulunamazsa None."""
        return self._index.get(poi_id)


class PoiRepository(AbstractPoiRepository):
    """
    Takılabilir bir AbstractDataSource üzerinden POI erişimi sağlar.

    Strateji deseni: hangi DataSource inject edilirse o kullanılır.
    Şu an JsonDataSource ile çalışır; gelecekte başka kaynaklar da takılabilir.
    """

    def __init__(self, data_source: AbstractDataSource):
        self._data_source = data_source

    async def find_by_city(self, city: str) -> list[Poi]:
        """Verilen şehirdeki tüm POI'ları döner (büyük/küçük harf duyarsız)."""
        all_pois = self._data_source.load_all_pois()
        return [p for p in all_pois if p.city.lower() == city.lower()]

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        """
        Şehir ve kategori listesine göre POI filtreler.
        categories boşsa şehirdeki tüm POI'lar döner.
        Frontend key'leri DB değerlerine normalize edilir.
        """
        city_pois = await self.find_by_city(city)
        if not categories:
            return city_pois
        db_cats = _normalize_categories(categories)
        return [p for p in city_pois if p.category.lower() in db_cats]

    async def find_by_id(self, poi_id: str) -> Poi | None:
        """ID'ye göre tek POI döner; bulunamazsa None."""
        return self._data_source.load_by_id(poi_id)


# ── Supabase Data API implementasyonu ────────────────────────────

# Frontend CATEGORY_TREE key'lerinden DB'deki main_category_1 değerlerine eşleme.
# Alt kategoriler (archaeology, religious vb.) üst kategoriye yönlendirilir.
_CATEGORY_KEY_TO_DB: dict[str, str] = {
    # Üst kategoriler
    "museums":   "museums",
    "cultural":  "cultural heritage",
    "nature":    "nature",
    # Cultural Heritage alt kategorileri
    "archaeology":   "cultural heritage",
    "architecture":  "cultural heritage",
    "fortifications": "cultural heritage",
    "infrastructure": "cultural heritage",
    "religious":     "cultural heritage",
    "transport":     "cultural heritage",
    "monumental":    "cultural heritage",
    # Nature alt kategorileri
    "parks":    "nature",
    "terrain":  "nature",
    "water":    "nature",
    "wildlife": "nature",
}


def _normalize_categories(categories: list[str]) -> set[str]:
    """
    Frontend'den gelen kategori key'lerini DB'deki değerlere dönüştürür.
    Bilinmeyen key'ler olduğu gibi lowercase olarak bırakılır (gelecekteki
    yeni kategorilere karşı toleranslı davranmak için).
    """
    result = set()
    for cat in categories:
        lower = cat.lower()
        result.add(_CATEGORY_KEY_TO_DB.get(lower, lower))
    return result


# Supabase'deki pois tablosunda estimated_visit_duration kolonu yok;
# tüm POI'lar için sabit 60 dakika kullanılır.
_DEFAULT_VISIT_DURATION = 60

# Supabase'den çekilecek kolon listesi — sadece ihtiyaç duyulanlar
_POI_COLUMNS = "id, name, city, latitude, longitude, categories, main_category_1"


def _row_to_poi(row: dict) -> Poi:
    """
    Supabase'den dönen satır dict'ini Poi domain nesnesine dönüştürür.

    Alan dönüşümleri:
      id             → str()  (tabloda INTEGER, domain'de str)
      main_category_1 → Poi.category  (yoksa categories[0], o da yoksa 'Other')
      estimated_visit_duration → tabloda yok, _DEFAULT_VISIT_DURATION sabiti kullanılır
    """
    raw_cats = row.get("categories") or []
    category = (
        row.get("main_category_1")
        or (raw_cats[0] if raw_cats else "Other")
    )
    return Poi(
        id=str(row["id"]),
        name=row["name"],
        category=category,
        city=row["city"],
        location=GeoPoint(
            latitude=row["latitude"],
            longitude=row["longitude"],
        ),
        estimated_visit_duration=_DEFAULT_VISIT_DURATION,
    )


class PostgresPoiRepository(AbstractPoiRepository):
    """
    Supabase Data API (PostgREST) üzerinden POI erişimi sağlar.

    Kategori filtresi ağ trafiğini azaltmak için Python tarafında uygulanır:
    önce şehrin tüm POI'ları çekilir, ardından kategori eşleştirmesi
    büyük/küçük harf duyarsız biçimde in-memory yapılır.
    """

    def __init__(self, client):
        self._client = client

    async def find_by_city(self, city: str) -> list[Poi]:
        """Verilen şehirdeki tüm POI'ları Supabase'den çeker (büyük/küçük harf duyarsız)."""
        response = await (
            self._client.table("pois")
            .select(_POI_COLUMNS)
            .ilike("city", city)
            .execute()
        )
        return [_row_to_poi(r) for r in response.data]

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        """
        Şehir ve kategori listesine göre POI filtreler.
        categories boşsa şehirdeki tüm POI'lar döner.
        Frontend key'leri DB değerlerine normalize edilir; filtreleme
        Python tarafında uygulanır.
        """
        all_pois = await self.find_by_city(city)
        if not categories:
            return all_pois
        db_cats = _normalize_categories(categories)
        return [p for p in all_pois if p.category.lower() in db_cats]

    async def find_by_id(self, poi_id: str) -> Poi | None:
        """ID'ye göre tek POI döner; bulunamazsa None."""
        response = await (
            self._client.table("pois")
            .select(_POI_COLUMNS)
            .eq("id", int(poi_id))
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return _row_to_poi(response.data[0])
