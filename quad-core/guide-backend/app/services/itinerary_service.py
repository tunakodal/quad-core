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


class ItineraryService:
    """
    Güzergah oluşturma ve yeniden planlama işlemlerini orkestre eder.
    Planlama kararlarını MonteCarloItineraryPlanner'a devreder.
    """

    def __init__(self, planner: MonteCarloItineraryPlanner):
        self.planner = planner

    async def build_itinerary(
        self, pois: list[Poi], constraints: TravelConstraints, prefs: TravelPreferences
    ) -> Itinerary:
        """
        Verilen POI listesinden kısıtlar ve tercihler doğrultusunda
        en iyi güzergahı oluşturur.
        """
        return self.planner.select_best(pois, constraints, prefs)

    async def replan(
            self,
            existing: Itinerary,
            edits: UserEdits,
            constraints: TravelConstraints,
            prefs: TravelPreferences,
    ) -> Itinerary:
        """
        Applies user edits to an existing itinerary.

        Current behavior:
        - removes POIs listed in removed_poi_ids
        - applies intra-day reorder operations exactly as requested
        - preserves unaffected days as-is

        Route recomputation is handled separately by RoutingService.
        """
        # 1) remove
        new_days: list[DayPlan] = []
        removed_ids = set(edits.removed_poi_ids)

        for day in existing.days:
            remaining_pois = [
                poi for poi in day.pois
                if poi.id not in removed_ids
            ]
            new_days.append(
                DayPlan(day_index=day.day_index, pois=remaining_pois)
            )

        # 2) reorder
        reorder_map = {
            op.day_index: op.ordered_poi_ids
            for op in edits.reorder_operations
        }

        for day in new_days:
            if day.day_index not in reorder_map:
                continue

            requested_order = reorder_map[day.day_index]
            poi_by_id = {poi.id: poi for poi in day.pois}

            # keep only IDs that still exist after removal
            reordered = [
                poi_by_id[poi_id]
                for poi_id in requested_order
                if poi_id in poi_by_id
            ]

            # append any leftover POIs not mentioned in the reorder request
            leftover = [
                poi for poi in day.pois
                if poi.id not in requested_order
            ]

            day.pois = reordered + leftover
        
        return Itinerary(days=new_days)
