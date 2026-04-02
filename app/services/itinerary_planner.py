"""
Monte Carlo güzergah planlayıcı — rastgele örnekleme ile aday planlar üretir
ve en yüksek puanlıyı PlanRanker aracılığıyla seçer.
"""
from app.models.poi import Poi
from app.models.route import Itinerary
from app.schemas.travel import TravelConstraints, TravelPreferences
from app.services.itinerary_builder import ItineraryBuilder
from app.services.plan_ranker import PlanRanker


class MonteCarloItineraryPlanner:
    """
    Birden fazla aday güzergah üretir ve en iyisini seçer.

    generate_candidates() şu an deterministik tek plan döndürmektedir.
    Monte Carlo sampling implementasyonu bu metodun içine yazılacak;
    dışarıya açık arayüz (parametre ve dönüş tipleri) sabit kalacaktır.
    """

    def __init__(
        self,
        itinerary_builder: ItineraryBuilder,
        plan_ranker: PlanRanker,
        max_iterations: int = 100,
        random_seed: int | None = None,
    ):
        self.itinerary_builder = itinerary_builder
        self.plan_ranker = plan_ranker
        self.max_iterations = max_iterations
        self.random_seed = random_seed

    def generate_candidates(
        self, pois: list[Poi], constraints: TravelConstraints
    ) -> list[Itinerary]:
        """
        Verilen POI listesinden aday güzergahlar üretir.

        Şu an tek deterministik plan döndürür.
        Monte Carlo implementasyonu: POI listesini max_iterations kez rastgele
        karıştırarak her seferinde farklı bir aday plan oluşturacak.
        """
        return [self.itinerary_builder.allocate_to_days(pois, constraints)]

    def select_best(
        self,
        pois: list[Poi],
        constraints: TravelConstraints,
        prefs: TravelPreferences,
    ) -> Itinerary:
        """Aday güzergahlar üretir ve en yüksek puanlıyı döner."""
        candidates = self.generate_candidates(pois, constraints)
        return self.select_best_from_candidates(candidates, constraints, prefs)

    def select_best_from_candidates(
        self,
        candidates: list[Itinerary],
        constraints: TravelConstraints,
        prefs: TravelPreferences,
    ) -> Itinerary:
        """
        Verilen aday listesini puanlar ve en iyisini döner.
        Liste boşsa boş bir Itinerary döner.
        """
        if not candidates:
            return Itinerary()
        return max(candidates, key=lambda c: self.plan_ranker.score(c, prefs, constraints))
