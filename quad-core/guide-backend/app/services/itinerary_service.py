"""
Itinerary service — orchestrates itinerary construction and stateless replanning.

Delegates the actual planning logic to MonteCarloItineraryPlanner.
"""
from app.models.poi import Poi
from app.models.route import Itinerary
from app.schemas.route_dtos import UserEdits
from app.schemas.travel import TravelConstraints, TravelPreferences
from app.services.itinerary_planner import MonteCarloItineraryPlanner


class ItineraryService:
    """
    Orchestrates itinerary construction and replanning.
    Delegates planning to MonteCarloItineraryPlanner.
    """

    def __init__(self, planner: MonteCarloItineraryPlanner):
        self.planner = planner

    async def build_itinerary(
        self, pois: list[Poi], constraints: TravelConstraints, prefs: TravelPreferences
    ) -> Itinerary:
        return self.planner.select_best(pois, constraints, prefs)

    async def replan(
        self,
        existing: Itinerary,
        edits: UserEdits,
        constraints: TravelConstraints,
        prefs: TravelPreferences,
    ) -> Itinerary:
        """
        Apply user edits deterministically and rebuild affected days.
        Backend is stateless — full itinerary context comes from client.
        """
        all_pois: list[Poi] = [
            poi
            for day in existing.days
            for poi in day.pois
            if poi.id not in edits.removed_poi_ids
        ]

        # TODO: honour locked_pois_by_day placement when Tuna's planner is ready
        return self.planner.select_best(all_pois, constraints, prefs)
