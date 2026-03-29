"""
POI data source and repository implementations.

Currently backed by a JSON file (JsonDataSource).
PostgreSQL implementation (PostgresDataSource) is pending — see TODO below.
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
