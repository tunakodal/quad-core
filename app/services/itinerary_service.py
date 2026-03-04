from abc import ABC, abstractmethod
from app.models.domain import Poi, Itinerary, DayPlan
from app.schemas.dtos import TravelConstraints, TravelPreferences, UserEdits


# ── PlanRanker interface ───────────────────────────────────────────

class PlanRanker(ABC):
    @abstractmethod
    def score(
        self,
        candidate: Itinerary,
        prefs: TravelPreferences,
        constraints: TravelConstraints,
    ) -> float:
        ...


class HeuristicPlanRanker(PlanRanker):
    """
    Baseline heuristic scoring:
    - category diversity
    - distance feasibility
    - visit duration balance
    """

    def score(
        self,
        candidate: Itinerary,
        prefs: TravelPreferences,
        constraints: TravelConstraints,
    ) -> float:
        if not candidate.days:
            return 0.0

        # Simple baseline: penalize days that exceed max distance
        penalty = 0.0
        for day in candidate.days:
            if day.route_segment:
                if day.route_segment.distance > constraints.max_daily_distance:
                    penalty += 1.0

        diversity = len({poi.category for day in candidate.days for poi in day.pois})
        return diversity - penalty


# ── ItineraryBuilder ──────────────────────────────────────────────

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


# ── MonteCarloItineraryPlanner (STUB — Erdem implement edecek) ────

class MonteCarloItineraryPlanner:
    """
    Generates multiple candidate itineraries via Monte Carlo sampling
    and selects the best one using PlanRanker.

    TODO: Implementation is owned by Erdem (Database & Algorithm).
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
        TODO: Generate `max_iterations` candidate itineraries by randomly
        sampling and reordering POIs, then return all candidates.
        """
        # Stub: returns a single deterministic allocation until implemented
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


# ── ItineraryService ──────────────────────────────────────────────

class ItineraryService:
    """
    Orchestrates itinerary construction and replanning.
    Delegates planning to MonteCarloItineraryPlanner.
    """

    def __init__(self, planner: MonteCarloItineraryPlanner):
        self.planner = planner

    async def build_itinerary(
        self, pois: list[Poi], constraints: TravelConstraints, prefs: TravelPreferences
    ) -> Itinerary:
        return self.planner.select_best(pois, constraints, prefs)

    async def replan(
        self,
        existing: Itinerary,
        edits: UserEdits,
        constraints: TravelConstraints,
        prefs: TravelPreferences,
    ) -> Itinerary:
        """
        Apply user edits deterministically and rebuild affected days.
        Backend is stateless — full itinerary context comes from client.
        """
        # Collect all current POIs
        all_pois: list[Poi] = [
            poi
            for day in existing.days
            for poi in day.pois
            if poi.id not in edits.removed_poi_ids
        ]

        # Respect locked POIs by day (keep their order, fill the rest)
        locked_ids: set[str] = {
            pid
            for ids in edits.locked_pois_by_day.values()
            for pid in ids
        }
        free_pois = [p for p in all_pois if p.id not in locked_ids]

        # For now, rebuild from remaining POIs
        # TODO: honour locked_pois_by_day placement when Erdem's planner is ready
        return self.planner.select_best(all_pois, constraints, prefs)
