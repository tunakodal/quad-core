"""
POI data source and repository implementations.

JsonDataSource  — JSON dosyasından okur (geliştirme / fallback).
PostgresPoiRepository — Supabase/PostgreSQL'den okur (production).

DB şema notu (gerçek tablo vs domain model farkları):
  - pois.id          → INTEGER  (domain: str, repository'de str(id) yapılır)
  - pois.categories  → TEXT[]   (domain: category str, main_category_1 kullanılır)
  - estimated_visit_duration → DB'de YOK, default 60 dk kullanılır
"""
from __future__ import annotations

import json
from pathlib import Path

from app.models.geo import GeoPoint
from app.models.poi import Poi
from app.repositories.interfaces import AbstractDataSource, AbstractPoiRepository


# TODO (Tuna): JsonDataSource yerine PostgresDataSource yaz.
#   - Aynı AbstractDataSource interface'ini kalıt
#   - load_all_pois()  → SELECT * FROM pois
#   - load_by_id(id)   → SELECT * FROM pois WHERE id = $1
#   - Her satırı Poi(..., location=GeoPoint(...)) nesnesine dönüştür
#   - Hazır olunca containers.py'deki JsonDataSource satırını değiştir
class JsonDataSource(AbstractDataSource):
    """Loads POI records from a JSON file on disk."""

    def __init__(self, json_path: str):
        self._pois: list[Poi] = []
        self._index: dict[str, Poi] = {}
        self._load(json_path)

    def _load(self, json_path: str) -> None:
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
        return list(self._pois)

    def load_by_id(self, poi_id: str) -> Poi | None:
        return self._index.get(poi_id)


class PoiRepository(AbstractPoiRepository):
    """Provides access to POI metadata via a pluggable DataSource."""

    def __init__(self, data_source: AbstractDataSource):
        self._data_source = data_source

    async def find_by_city(self, city: str) -> list[Poi]:
        all_pois = self._data_source.load_all_pois()
        return [p for p in all_pois if p.city.lower() == city.lower()]

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        city_pois = await self.find_by_city(city)
        if not categories:
            return city_pois
        cat_lower = {c.lower() for c in categories}
        return [p for p in city_pois if p.category.lower() in cat_lower]

    async def find_by_id(self, poi_id: str) -> Poi | None:
        return self._data_source.load_by_id(poi_id)


# ── PostgreSQL implementation ─────────────────────────────────────

_DEFAULT_VISIT_DURATION = 60  # DB'de estimated_visit_duration yok, 60 dk default


def _row_to_poi(row) -> Poi:
    """
    asyncpg Record → Poi domain nesnesi.

    Mapping notları:
      - row['id'] INTEGER → str(id)
      - row['main_category_1'] → domain category (yoksa categories[0], o da yoksa 'Other')
      - estimated_visit_duration → DB'de yok, _DEFAULT_VISIT_DURATION kullanılır
    """
    raw_cats = row["categories"] or []
    category = (
        row["main_category_1"]
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
    POI repository backed by Supabase/PostgreSQL.

    Kategori filtresi için PostgreSQL array overlap (&&) kullanır,
    büyük/küçük harf duyarsız karşılaştırma Python tarafında yapılır.
    """

    def __init__(self, pool):
        self._pool = pool

    async def find_by_city(self, city: str) -> list[Poi]:
        rows = await self._pool.fetch(
            """
            SELECT id, name, city, latitude, longitude,
                   categories, main_category_1
            FROM pois
            WHERE LOWER(city) = LOWER($1)
            """,
            city,
        )
        return [_row_to_poi(r) for r in rows]

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        if not categories:
            return await self.find_by_city(city)

        # Büyük/küçük harf duyarsız array overlap:
        # DB'deki her kategori ile kullanıcının seçtiği kategoriler LOWER bazında karşılaştırılır
        cat_lower = [c.lower() for c in categories]
        rows = await self._pool.fetch(
            """
            SELECT id, name, city, latitude, longitude,
                   categories, main_category_1
            FROM pois
            WHERE LOWER(city) = LOWER($1)
              AND EXISTS (
                  SELECT 1 FROM unnest(categories) AS c
                  WHERE LOWER(c) = ANY($2::text[])
              )
            """,
            city,
            cat_lower,
        )
        return [_row_to_poi(r) for r in rows]

    async def find_by_id(self, poi_id: str) -> Poi | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, name, city, latitude, longitude,
                   categories, main_category_1
            FROM pois
            WHERE id = $1
            """,
            int(poi_id),
        )
        return _row_to_poi(row) if row else None
