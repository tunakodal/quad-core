"""
Monte Carlo itinerary planner — generates candidate itineraries via random sampling
and returns the highest-scoring one according to a PlanRanker.
"""
from app.models.poi import Poi
from app.models.route import Itinerary
from app.schemas.travel import TravelConstraints, TravelPreferences
from app.services.itinerary_builder import ItineraryBuilder
from app.services.plan_ranker import PlanRanker


class MonteCarloItineraryPlanner:
    """
    Generates multiple candidate itineraries via Monte Carlo sampling
    and selects the best one using PlanRanker.

    TODO: Implementation is owned by Tuna (Database & Algorithm).
          The interface below must remain stable.
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
        TODO (Tuna): Bu metodun içini doldur. Mantık şu şekilde olmalı:
            rng = random.Random(self.random_seed)
            candidates = []
            for _ in range(self.max_iterations):
                shuffled = list(pois)
                rng.shuffle(shuffled)
                candidate = self.itinerary_builder.allocate_to_days(shuffled, constraints)
                candidates.append(candidate)
            return candidates
        Metod imzasını (parametre ve dönüş tipi) değiştirme.
        """
        # Stub: tek bir deterministik allocation döndürür, implement edilene kadar
        return [self.itinerary_builder.allocate_to_days(pois, constraints)]

    def select_best(
        self,
        pois: list[Poi],
        constraints: TravelConstraints,
        prefs: TravelPreferences,
    ) -> Itinerary:
        """Generate candidates and return the highest-scoring one."""
        candidates = self.generate_candidates(pois, constraints)
        return self.select_best_from_candidates(candidates, constraints, prefs)

    def select_best_from_candidates(
        self,
        candidates: list[Itinerary],
        constraints: TravelConstraints,
        prefs: TravelPreferences,
    ) -> Itinerary:
        """Score all candidates and return the best."""
        if not candidates:
            return Itinerary()
        return max(candidates, key=lambda c: self.plan_ranker.score(c, prefs, constraints))
