from app.models.poi import Poi
from app.schemas.travel import TravelConstraints, TravelPreferences


class PoiService:
    """
    Selects candidate POIs from the curated dataset based on user
    preferences (city, categories) and basic feasibility filters.
    """

    def __init__(self, poi_repository):
        """POI repository bagimliligini alir ve saklar."""
        self.poi_repository = poi_repository

    async def get_candidate_pois(self, prefs: TravelPreferences) -> list[Poi]:
        """Return POIs matching city and category filters."""
        return await self.poi_repository.find_by_city_and_categories(
            city=prefs.city,
            categories=prefs.categories,
        )

    async def count_available_pois(self, city: str, categories: list[str]) -> int:
        """Verilen sehir ve kategoriler icin uygun POI sayisini doner."""
        pois = await self.poi_repository.find_by_city_and_categories(city, categories)
        return len(pois)


    async def get_random_pois(self, limit: int) -> list[Poi]:
        """Kesif kullanim durumu icin rastgele POI listesi doner."""
        return await self.poi_repository.find_random(limit)

