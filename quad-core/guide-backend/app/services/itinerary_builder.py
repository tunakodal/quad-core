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

    def build_day_plan(
            self,
            pois: list[Poi],
            day_index: int,
    ) -> DayPlan:
        """
        Seçilmiş bir günlük POI listesinden DayPlan oluşturur.
        Günlere bölme kararı burada verilmez.
        """
        return DayPlan(
            day_index=day_index,
            pois=pois,
        )

    def build_itinerary_from_days(
            self,
            day_plans: list[DayPlan],
    ) -> Itinerary:
        """
        Hazır DayPlan listesinden Itinerary oluşturur.
        """
        return Itinerary(days=day_plans)
