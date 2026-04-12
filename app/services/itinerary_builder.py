"""
Itinerary builder — düz POI listesini kısıtlar altında günlük planlara böler.
"""
from app.models.poi import Poi
from app.models.route import DayPlan, Itinerary
from app.schemas.travel import TravelConstraints


class ItineraryBuilder:
    """
    Düz bir POI listesini kısıtlara (max_pois_per_day, max_trip_days) göre
    günlük planlara böler.

    Sıralama değiştirilmez: POI'lar girdi sırasıyla günlere atanır.
    MonteCarloItineraryPlanner bu sınıfı farklı sıralamalarla çağırarak
    çeşitli aday planlar üretir.
    """

    def allocate_to_days(
        self, pois: list[Poi], constraints: TravelConstraints
    ) -> Itinerary:
        """
        POI listesini günlere bölerek Itinerary döner.

        Her gün en fazla max_pois_per_day POI alır.
        Toplam gün sayısı max_trip_days'i geçemez; fazla POI'lar atlanır.
        """
        days: list[DayPlan] = []
        chunk_size = constraints.max_pois_per_day

        for day_idx, start in enumerate(range(0, len(pois), chunk_size), start=1):
            if day_idx > constraints.max_trip_days:
                break
            chunk = pois[start : start + chunk_size]
            days.append(DayPlan(day_index=day_idx, pois=chunk))

        return Itinerary(days=days)
