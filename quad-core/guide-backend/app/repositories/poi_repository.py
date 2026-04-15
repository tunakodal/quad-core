"""
POI data source and repository implementations.

Two strategies:
  JsonDataSource / PoiRepository      — reads from JSON (development / fallback)
  PostgresPoiRepository               — reads from Supabase Data API (production)

DB ↔ domain model mapping (handled in PostgresPoiRepository):
  pois.id              INTEGER  → Poi.id: str   (converted using str())

Taxonomy fields:
  pois.categories, main_category_1/2, sub_category_1/2/3/4
    → mapped to Poi taxonomy fields
    category is retained for compatibility and display purposes.

IMPORTANT:
  - Filtering and diversity logic rely on sub_category_* fields as the source of truth.
  - The category field is no longer the primary classification source.

Estimated visit duration:
  - Not stored in the database.
  - Computed dynamically via `_compute_estimated_visit_duration(...)`.
  - Calculation is based on:
      - subcategory-based base durations
      - review count multiplier
      - rating multiplier
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
                category=item.get("category", "Other"),

                main_category_1=item.get("main_category_1"),
                main_category_2=item.get("main_category_2"),
                sub_category_1=item.get("sub_category_1"),
                sub_category_2=item.get("sub_category_2"),
                sub_category_3=item.get("sub_category_3"),
                sub_category_4=item.get("sub_category_4"),

                city=item["city"],
                location=GeoPoint(
                    latitude=item["location"]["latitude"],
                    longitude=item["location"]["longitude"],
                ),
                estimated_visit_duration=item.get("estimated_visit_duration", 60),
                google_rating=item.get("google_rating"),
                google_reviews_total=item.get("google_reviews_total"),
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
        Filters POIs by city and requested categories.
        If categories is empty, returns all POIs in the city.
        Category filtering is based on POI subcategories.
        """
        city_pois = await self.find_by_city(city)
        if not categories:
            return city_pois

        return [p for p in city_pois if _poi_matches_categories(p, categories)]

    async def find_by_id(self, poi_id: str) -> Poi | None:
        """ID'ye göre tek POI döner; bulunamazsa None."""
        return self._data_source.load_by_id(poi_id)


# ── Supabase Data API implementasyonu ────────────────────────────

_POI_COLUMNS = (
    "id, name, city, latitude, longitude, categories, "
    "main_category_1, main_category_2, "
    "sub_category_1, sub_category_2, sub_category_3, sub_category_4, "
    "google_rating, google_reviews_total"
)
def _compute_estimated_visit_duration(row: dict) -> int:
    """
    Computes estimated visit duration (minutes) according to the report logic:

    1. Category-based base duration assignment
    2. Review-count adjustment
    3. Rating-based adjustment
    4. Final clipping and rounding

    For multiple categories:
        category_duration = 0.70 * max_duration + 0.30 * avg_duration
    """

    SUBCATEGORY_DURATION = {
        "Ancient & Archaeology": 120,
        "Museum": 120,
        "Fortifications": 90,
        "Civil & Traditional Architecture": 75,
        "Terrain & Landforms": 75,
        "Wildlife & Natural Experience": 75,
        "Parks & Outdoor": 60,
        "Water & Coastal": 60,
        "Urban & Monumental Heritage": 60,
        "Transportation as Heritage": 60,
        "Historical Infrastructure": 60,
        "Religious": 45,
    }

    DEFAULT_DURATION = 60

    categories = [
        row.get("sub_category_1"),
        row.get("sub_category_2"),
        row.get("sub_category_3"),
        row.get("sub_category_4"),
    ]
    categories = [c for c in categories if c]

    if categories:
        durations = [
            SUBCATEGORY_DURATION.get(category, DEFAULT_DURATION)
            for category in categories
        ]
        max_duration = max(durations)
        avg_duration = sum(durations) / len(durations)
        category_duration = 0.70 * max_duration + 0.30 * avg_duration
    else:
        category_duration = DEFAULT_DURATION

    reviews = row.get("google_reviews_total") or 0
    rating = row.get("google_rating") or 0

    # Review-count multiplier
    if reviews < 50:
        m_review = 0.90
    elif reviews < 200:
        m_review = 1.00
    elif reviews < 1000:
        m_review = 1.10
    else:
        m_review = 1.20

    # Rating-based multiplier
    if rating < 3.5:
        m_rating = 0.90
    elif rating < 4.2:
        m_rating = 1.00
    elif rating < 4.6:
        m_rating = 1.10
    else:
        m_rating = 1.20

    adjusted_duration = category_duration * m_review * m_rating

    duration = int(round(adjusted_duration / 5) * 5)
    duration = max(15, min(duration, 360))

    return duration

def _row_to_poi(row: dict) -> Poi:
    raw_cats = row.get("categories") or []

    category = (
        row.get("main_category_1")
        or row.get("sub_category_1")
        or (raw_cats[0] if raw_cats else "Other")
    )

    return Poi(
        id=str(row["id"]),
        name=row["name"],
        category=category,

        main_category_1=row.get("main_category_1"),
        main_category_2=row.get("main_category_2"),
        sub_category_1=row.get("sub_category_1"),
        sub_category_2=row.get("sub_category_2"),
        sub_category_3=row.get("sub_category_3"),
        sub_category_4=row.get("sub_category_4"),

        city=row["city"],
        location=GeoPoint(
            latitude=row["latitude"],
            longitude=row["longitude"],
        ),

        estimated_visit_duration=_compute_estimated_visit_duration(row),

        google_rating=row.get("google_rating"),
        google_reviews_total=row.get("google_reviews_total"),
    )

def _extract_poi_subcategories(poi: Poi) -> set[str]:
    return {
        c.lower()
        for c in [
            poi.sub_category_1,
            poi.sub_category_2,
            poi.sub_category_3,
            poi.sub_category_4,
        ]
        if c
    }


def _poi_matches_categories(poi: Poi, categories: list[str]) -> bool:
    if not categories:
        return True

    wanted = {c.lower() for c in categories}
    poi_subs = _extract_poi_subcategories(poi)

    return not wanted.isdisjoint(poi_subs)

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
        Filters POIs by city and requested categories.
        If categories is empty, returns all POIs in the city.
        Category filtering is based on POI subcategories.
        """
        all_pois = await self.find_by_city(city)
        if not categories:
            return all_pois

        return [p for p in all_pois if _poi_matches_categories(p, categories)]

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
