"""
Itinerary builder — allocates a flat list of POIs into day plans under constraints.
"""
from app.models.poi import Poi
from app.models.route import DayPlan, Itinerary
from app.schemas.travel import TravelConstraints


class ItineraryBuilder:
    """Allocates a flat list of POIs into day plans under constraints."""

    def allocate_to_days(
        self, pois: list[Poi], constraints: TravelConstraints
    ) -> Itinerary:
        days: list[DayPlan] = []
        chunk_size = constraints.max_pois_per_day

        for day_idx, start in enumerate(range(0, len(pois), chunk_size), start=1):
            if day_idx > constraints.max_trip_days:
                break
            chunk = pois[start : start + chunk_size]
            days.append(DayPlan(day_index=day_idx, pois=chunk))

        return Itinerary(days=days)
