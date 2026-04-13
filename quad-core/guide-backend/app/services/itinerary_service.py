"""
Itinerary service — güzergah oluşturma ve durumsuz yeniden planlama.

Planlama mantığını MonteCarloItineraryPlanner'a devreder.
Backend tamamen durumsuz çalışır: her yeniden planlama isteğinde
mevcut güzergah context'i client tarafından gönderilir.
"""
from app.models.poi import Poi
from app.models.route import Itinerary, DayPlan
from app.schemas.route_dtos import UserEdits
from app.schemas.travel import TravelConstraints, TravelPreferences
from app.services.itinerary_planner import MonteCarloItineraryPlanner
from app.repositories.interfaces import AbstractPoiRepository
from app.schemas.common import ApiWarning
from app.schemas.common import Severity

class ItineraryService:
    """
    Güzergah oluşturma ve yeniden planlama işlemlerini orkestre eder.
    Planlama kararlarını MonteCarloItineraryPlanner'a devreder.
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

        warnings: list[ApiWarning] = []

        existing_map = {
            poi.id: poi
            for day in existing.days
            for poi in day.pois
        }

        if edits.ordered_poi_ids_by_day:
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
                        raise ValueError(f"Unknown POI id in replanning request: {pid}")

                    pois.append(poi)

                new_days.append(
                    DayPlan(day_index=day.day_index, pois=pois)
                )

            return Itinerary(days=new_days), warnings

        if edits.selected_poi_ids:
            selected_ids = set(edits.selected_poi_ids)

            new_days: list[DayPlan] = []

            for day in existing.days:
                filtered = [
                    poi for poi in day.pois
                    if poi.id in selected_ids
                ]
                new_days.append(
                    DayPlan(day_index=day.day_index, pois=filtered)
                )

            return Itinerary(days=new_days), warnings

        new_days: list[DayPlan] = []
        removed_ids = set(edits.removed_poi_ids)

        for day in existing.days:
            remaining = [
                poi for poi in day.pois
                if poi.id not in removed_ids
            ]
            new_days.append(
                DayPlan(day_index=day.day_index, pois=remaining)
            )

        reorder_map = {
            op.day_index: op.ordered_poi_ids
            for op in edits.reorder_operations
        }

        for day in new_days:
            if day.day_index not in reorder_map:
                continue

            order = reorder_map[day.day_index]
            poi_by_id = {p.id: p for p in day.pois}

            reordered = [
                poi_by_id[i]
                for i in order
                if i in poi_by_id
            ]

            leftover = [
                p for p in day.pois
                if p.id not in order
            ]

            day.pois = reordered + leftover

        return Itinerary(days=new_days), warnings
