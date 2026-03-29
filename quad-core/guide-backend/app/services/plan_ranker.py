"""
Plan ranking strategies — score candidate itineraries to select the best one.
"""
from abc import ABC, abstractmethod

from app.models.route import Itinerary
from app.schemas.travel import TravelConstraints, TravelPreferences


class PlanRanker(ABC):
    @abstractmethod
    def score(
        self,
        candidate: Itinerary,
        prefs: TravelPreferences,
        constraints: TravelConstraints,
    ) -> float: ...


class HeuristicPlanRanker(PlanRanker):
    """
    Baseline heuristic scoring:
      - rewards category diversity across days
      - penalises days that exceed max_daily_distance
    """

    def score(
        self,
        candidate: Itinerary,
        prefs: TravelPreferences,
        constraints: TravelConstraints,
    ) -> float:
        if not candidate.days:
            return 0.0

        penalty = 0.0
        for day in candidate.days:
            if day.route_segment:
                if day.route_segment.distance > constraints.max_daily_distance:
                    penalty += 1.0

        diversity = len({poi.category for day in candidate.days for poi in day.pois})
        return diversity - penalty
