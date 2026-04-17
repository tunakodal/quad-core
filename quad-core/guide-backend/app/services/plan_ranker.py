"""
Plan scoring strategies -- evaluates candidate routes and selects the best one.

Strategy pattern: implement PlanRanker ABC to swap scoring algorithms at runtime.
"""
from abc import ABC, abstractmethod

from app.models.route import Itinerary
from app.schemas.travel import TravelConstraints, TravelPreferences


class PlanRanker(ABC):
    """Abstract scorer that assigns a numeric score to a candidate itinerary."""

    @abstractmethod
    def score(
        self,
        candidate: Itinerary,
        prefs: TravelPreferences,
        constraints: TravelConstraints,
    ) -> float:
        """
        Score the itinerary; higher is better.
        Only used for comparison -- absolute value has no meaning.
        """
        ...


class HeuristicPlanRanker(PlanRanker):
    """
    Basic heuristic scoring:
      + Rewards category diversity across days (one point per distinct category)
      - Penalises each day that exceeds max_daily_distance (-1.0 per violation)
    """

    def score(
        self,
        candidate: Itinerary,
        prefs: TravelPreferences,
        constraints: TravelConstraints,
    ) -> float:
        """
        Returns a heuristic score rewarding diversity and penalising distance violations.

        Returns 0.0 for an empty itinerary. Higher score means better plan;
        absolute value is meaningless -- use only for ranking.
        """
        if not candidate.days:
            return 0.0

        # Distance violation penalty: -1.0 per offending day
        penalty = 0.0
        for day in candidate.days:
            if day.route_segment:
                if day.route_segment.distance > constraints.max_daily_distance:
                    penalty += 1.0

        # Diversity bonus: how many distinct sub-categories appear across the whole trip
        diversity = len({
            c
            for day in candidate.days
            for poi in day.pois
            for c in [
                poi.sub_category_1,
                poi.sub_category_2,
                poi.sub_category_3,
                poi.sub_category_4,
            ]
            if c
        })

        return diversity - penalty
