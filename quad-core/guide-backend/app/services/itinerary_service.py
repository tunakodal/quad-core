from app.models.poi import Poi
from app.models.route import Itinerary, DayPlan
from app.schemas.route_dtos import UserEdits
from app.schemas.travel import TravelConstraints, TravelPreferences
from app.services.itinerary_planner import MonteCarloItineraryPlanner
from app.repositories.interfaces import AbstractPoiRepository
from app.schemas.common import ApiWarning, Severity


class ItineraryService:

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

        if not edits.ordered_poi_ids_by_day:
            return existing, warnings

        # Mevcut POI'leri map'le
        existing_map = {
            poi.id: poi
            for day in existing.days
            for poi in day.pois
        }

        new_days: list[DayPlan] = []

        for day in existing.days:
            requested_ids = edits.ordered_poi_ids_by_day.get(day.day_index)

            # Bu gün modified değilse aynen koru
            if requested_ids is None:
                new_days.append(day)
                continue

            # Modified gün — POI'leri sırayla topla
            pois: list[Poi] = []
            seen: set[str] = set()

            for pid in requested_ids:
                if pid in seen:
                    continue
                seen.add(pid)

                poi = existing_map.get(pid)

                # Yeni eklenen POI — DB'den al
                if poi is None:
                    poi = await self.poi_repository.find_by_id(pid)

                if poi is None:
                    warnings.append(
                        ApiWarning(
                            code="POI_NOT_FOUND",
                            severity=Severity.WARN,
                            message=f"POI with id '{pid}' could not be found, skipped.",
                        )
                    )
                    continue

                pois.append(poi)

            new_days.append(
                DayPlan(day_index=day.day_index, pois=pois)
            )

        return Itinerary(days=new_days), warnings