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
        """
        Returns the count of POIs available for the given city and categories.

        Used by the suggest-days endpoint to estimate a feasible trip length.
        Loads all matching POIs and counts them; for large datasets this could
        be optimised with a dedicated COUNT query in the repository.
        """
        pois = await self.poi_repository.find_by_city_and_categories(city, categories)
        return len(pois)

    async def get_random_pois(self, limit: int) -> list[Poi]:
        """
        Returns a random selection of POIs from the database.

        Intended for 'Featured' or 'Explore' UI components that need
        a varied sample without any city/category filter.

        Args:
            limit: Maximum number of POIs to return.

        Returns:
            A randomly ordered list of Poi objects, at most `limit` items long.
        """
        return await self.poi_repository.find_random(limit)
