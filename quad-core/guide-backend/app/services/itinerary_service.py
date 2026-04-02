"""
Itinerary service — güzergah oluşturma ve durumsuz yeniden planlama.

Planlama mantığını MonteCarloItineraryPlanner'a devreder.
Backend tamamen durumsuz çalışır: her yeniden planlama isteğinde
mevcut güzergah context'i client tarafından gönderilir.
"""
from app.models.poi import Poi
from app.models.route import Itinerary
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
        Kullanıcı düzenlemelerini mevcut güzergaha uygular ve yeniden planlar.

        Silinen POI'lar çıkarılır, kalan tüm POI'lar planlayıcıya tekrar
        verilir. Backend durumsuz olduğundan tam güzergah context'i
        client'tan alınır.

        Kilitli POI'ların (locked_pois_by_day) sabit gün ataması
        planlayıcı geliştirildiğinde bu metodda desteklenecektir.
        """
        all_pois: list[Poi] = [
            poi
            for day in existing.days
            for poi in day.pois
            if poi.id not in edits.removed_poi_ids
        ]
        return self.planner.select_best(all_pois, constraints, prefs)
