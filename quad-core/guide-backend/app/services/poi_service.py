from app.models.poi import Poi
from app.schemas.travel import TravelConstraints, TravelPreferences


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

    async def count_available_pois(self, city: str, categories: list[str]) -> int:
        pois = await self.poi_repository.find_by_city_and_categories(city, categories)
        print(len(pois))
        return len(pois)
