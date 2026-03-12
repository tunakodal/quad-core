from app.models.domain import Poi
from app.schemas.dtos import TravelPreferences, TravelConstraints


class PoiService:
    """
    Selects candidate POIs from the curated dataset based on user
    preferences (city, categories) and basic feasibility filters.
    """

    def __init__(self, poi_repository):
        self.poi_repository = poi_repository

    async def get_candidate_pois(self, prefs: TravelPreferences) -> list[Poi]:
        """Return POIs matching city and category filters."""
        return await self.poi_repository.find_by_city_and_categories(
            city=prefs.city,
            categories=prefs.categories,
        )

    async def filter_by_constraints(
        self, pois: list[Poi], constraints: TravelConstraints
    ) -> list[Poi]:
        """Apply hard feasibility filters (max total POIs etc.)."""
        max_total = constraints.max_trip_days * constraints.max_pois_per_day
        return pois[:max_total]

    async def count_available_pois(self, city: str, categories: list[str]) -> int:
        pois = await self.poi_repository.find_by_city_and_categories(city, categories)
        return len(pois)
