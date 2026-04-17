"""
POI data source and repository implementations.

Two strategies:
  JsonDataSource / PoiRepository  -- reads from JSON (development / fallback)
  PostgresPoiRepository           -- reads from Supabase Data API (production)

DB <-> domain model mapping (PostgresPoiRepository):
  pois.id   INTEGER -> Poi.id: str  (converted with str())

Taxonomy fields:
  pois.categories, main_category_1/2, sub_category_1/2/3/4
    -> mapped to Poi taxonomy fields.
    category is retained for UI/filter compatibility.

IMPORTANT:
  - Filtering and diversity logic rely on sub_category_* fields as the source of truth.
  - The category field is no longer the primary classification source.

Estimated visit duration:
  - Not stored in the database.
  - Computed dynamically via _compute_estimated_visit_duration().
  - Based on: subcategory base durations, review count multiplier, rating multiplier.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from app.models.geo import GeoPoint
from app.models.poi import Poi
from app.repositories.interfaces import AbstractDataSource, AbstractPoiRepository


# -- JSON / development implementation --

class JsonDataSource(AbstractDataSource):
    """
    Loads POI records from a JSON file on disk.

    Used in development and as a fallback when Supabase is not configured.
    If the file does not exist, silently returns an empty list.
    """

    def __init__(self, json_path: str):
        self._pois: list[Poi] = []
        self._index: dict[str, Poi] = {}
        self._load(json_path)

    def _load(self, json_path: str) -> None:
        """Reads and deserialises the JSON file into memory."""
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
        """Returns all loaded POIs."""
        return list(self._pois)

    def load_by_id(self, poi_id: str) -> Poi | None:
        """Returns the POI with the given ID, or None if not found."""
        return self._index.get(poi_id)


class PoiRepository(AbstractPoiRepository):
    """
    Provides POI access via a pluggable AbstractDataSource.

    Strategy pattern: whichever DataSource is injected is used.
    Currently backed by JsonDataSource; other sources can be wired in.
    """

    def __init__(self, data_source: AbstractDataSource):
        self._data_source = data_source

    async def find_by_city(self, city: str) -> list[Poi]:
        """Returns all POIs in the given city (case-insensitive)."""
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
        """Returns a single POI by ID, or None if not found."""
        return self._data_source.load_by_id(poi_id)

    async def find_random(self, limit: int) -> list[Poi]:
        """Returns up to `limit` randomly selected POIs from the full dataset."""
        all_pois = self._data_source.load_all_pois()
        return random.sample(all_pois, min(limit, len(all_pois)))


# -- Supabase Data API implementation --

_POI_COLUMNS = (
    "id, name, city, latitude, longitude, categories, "
    "main_category_1, main_category_2, "
    "sub_category_1, sub_category_2, sub_category_3, sub_category_4, "
    "google_rating, google_reviews_total"
)


def _compute_estimated_visit_duration(row: dict) -> int:
    """
    Computes the estimated visit duration (minutes) for a POI.

    Not stored in the DB; computed dynamically on each call.
    Based on three factors:
      1. Subcategory base duration (e.g. Museum: 75 min, Religious: 30 min)
      2. Review count multiplier: few reviews -> 0.90x, many -> 1.10x
      3. Rating multiplier: low rating -> 0.90x, high -> 1.10x

    Result is rounded to 5 minutes and clamped to [15, 150].

    Args:
        row: Raw POI data from Supabase (expects sub_category_* and google_* fields).

    Returns:
        Estimated visit duration in minutes.
    """
    SUBCATEGORY_DURATION = {
        "Ancient & Archaeology": 75,
        "Museum": 75,
        "Fortifications": 60,
        "Civil & Traditional Architecture": 50,
        "Terrain & Landforms": 50,
        "Wildlife & Natural Experience": 50,
        "Parks & Outdoor": 40,
        "Water & Coastal": 40,
        "Urban & Monumental Heritage": 40,
        "Transportation as Heritage": 40,
        "Historical Infrastructure": 40,
        "Religious": 30,
    }

    DEFAULT_DURATION = 40

    categories = [
        row.get("sub_category_1"),
        row.get("sub_category_2"),
        row.get("sub_category_3"),
        row.get("sub_category_4"),
    ]
    categories = [c for c in categories if c]

    if categories:
        durations = [SUBCATEGORY_DURATION.get(c, DEFAULT_DURATION) for c in categories]
        max_duration = max(durations)
        avg_duration = sum(durations) / len(durations)
        category_duration = 0.70 * max_duration + 0.30 * avg_duration
    else:
        category_duration = DEFAULT_DURATION

    reviews = row.get("google_reviews_total") or 0
    rating = row.get("google_rating") or 0

    m_review = 0.90 if reviews < 50 else (1.10 if reviews >= 500 else 1.00)
    m_rating = 0.90 if rating < 3.5 else (1.10 if rating >= 4.5 else 1.00)

    adjusted_duration = category_duration * m_review * m_rating
    duration = int(round(adjusted_duration / 5) * 5)
    return max(15, min(duration, 150))


def _row_to_poi(row: dict) -> Poi:
    """
    Converts a raw Supabase row into a Poi domain model.

    The category field is kept for compatibility; priority order:
    main_category_1 > sub_category_1 > first element of categories list > "Other"

    estimated_visit_duration is computed dynamically on each call.
    """
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
    """Returns the non-empty sub_category fields of a POI as a lowercase set."""
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
    """
    Returns True if at least one of the POI's subcategories matches the requested list.

    Comparison is case-insensitive. If categories is empty, every POI matches.
    """
    if not categories:
        return True
    wanted = {c.lower() for c in categories}
    poi_subs = _extract_poi_subcategories(poi)
    return not wanted.isdisjoint(poi_subs)


class PostgresPoiRepository(AbstractPoiRepository):
    """
    Provides POI access via the Supabase Data API (PostgREST).

    Category filtering is applied in Python to reduce network traffic:
    all POIs for the city are fetched first, then filtered in-memory
    with case-insensitive subcategory matching.
    """

    def __init__(self, client):
        self._client = client

    async def find_by_city(self, city: str) -> list[Poi]:
        """Fetches all POIs for the given city from Supabase (case-insensitive)."""
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
        """Returns a single POI by ID, or None if not found."""
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

    async def find_random(self, limit: int) -> list[Poi]:
        """
        Returns random POIs from the database.

        Fetches 200-row batches from 3 random offsets, shuffles and
        returns the first `limit` results. Not guaranteed to be perfectly random;
        intended for discovery/exploration use cases.
        """
        batches = []
        for _ in range(3):
            offset = random.randint(0, 2000)
            res = await (
                self._client.table("pois")
                .select(_POI_COLUMNS)
                .range(offset, offset + 200)
                .execute()
            )
            batches.extend(res.data)

        pois = [_row_to_poi(r) for r in batches]
        random.shuffle(pois)
        return pois[:limit]
