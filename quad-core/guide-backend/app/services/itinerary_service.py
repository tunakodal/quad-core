"""
Itinerary Service -- orchestration layer between planner and repository.

build_itinerary : Selects the best daily plan from a POI list via Monte Carlo planner.
replan          : Applies user edits to an existing itinerary; only rebuilds changed days.
"""
from app.models.poi import Poi
from app.models.route import Itinerary, DayPlan
from app.schemas.route_dtos import UserEdits
from app.schemas.travel import TravelConstraints, TravelPreferences
from app.services.itinerary_planner import MonteCarloItineraryPlanner
from app.repositories.interfaces import AbstractPoiRepository
from app.schemas.common import ApiWarning, Severity


class ItineraryService:
    """
    Manages itinerary creation and replanning business logic.

    Decoupled from the planner (MonteCarloItineraryPlanner); a different
    planning strategy can be injected to swap the algorithm.
    """

    def __init__(
        self,
        planner: MonteCarloItineraryPlanner,
        poi_repository: AbstractPoiRepository,
    ):
        self.planner = planner
        self.poi_repository = poi_repository

    async def build_itinerary(
        self, pois: list[Poi], constraints: TravelConstraints, prefs: TravelPreferences
    ) -> tuple[Itinerary, list[ApiWarning]]:
        """
        Builds the best itinerary from a POI list via the injected planner.

        If the number of generated days is less than the requested trip_days,
        a PARTIAL_ITINERARY warning is added -- this is not an error, just a
        signal that the POI pool was insufficient.

        Args:
            pois:        Candidate venues for planning.
            constraints: System limits such as max POIs/day and max distance.
            prefs:       User-requested trip length and city.

        Returns:
            (Itinerary, warnings) tuple.
        """
        itinerary = self.planner.select_best(pois, constraints, prefs)
        warnings: list[ApiWarning] = []
        if len(itinerary.days) < prefs.trip_days:
            warnings.append(
                ApiWarning(
                    code="PARTIAL_ITINERARY",
                    severity=Severity.WARN,
                    message="Requested trip duration could not be fully satisfied with available POIs.",
                )
            )
        return itinerary, warnings

    async def replan(
        self,
        existing: Itinerary,
        edits: UserEdits,
        constraints: TravelConstraints,
        prefs: TravelPreferences,
    ) -> tuple[Itinerary, list[ApiWarning]]:
        """
        Applies user edits to an existing itinerary; only rebuilds changed days.

        Days not listed in edits.ordered_poi_ids_by_day are preserved as-is.
        Newly added POI IDs (not in the existing plan) are fetched from the DB.

        Args:
            existing:    The current itinerary before edits.
            edits:       Which days changed and their new POI order.
            constraints: Current system limits.
            prefs:       User preferences (used for context only).

        Returns:
            (Itinerary, warnings) tuple.

        Raises:
            ValueError: If a referenced POI ID cannot be found in DB or existing plan.
        """
        warnings: list[ApiWarning] = []

        if not edits.ordered_poi_ids_by_day:
            return existing, warnings

        existing_map = {
            poi.id: poi
            for day in existing.days
            for poi in day.pois
        }

        new_days: list[DayPlan] = []

        for day in existing.days:
            requested_ids = edits.ordered_poi_ids_by_day.get(day.day_index)

            if requested_ids is None:
                new_days.append(day)
                continue

            pois: list[Poi] = []
            seen: set[str] = set()

            for pid in requested_ids:
                if pid in seen:
                    continue
                seen.add(pid)

                poi = existing_map.get(pid)

                if poi is None:
                    poi = await self.poi_repository.find_by_id(pid)

                if poi is None:
                    raise ValueError(f"POI with id '{pid}' could not be found.")

                pois.append(poi)

            new_days.append(
                DayPlan(day_index=day.day_index, pois=pois)
            )

        return Itinerary(days=new_days), warnings
