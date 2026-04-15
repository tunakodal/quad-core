"""
Unit tests for MonteCarloItineraryPlanner.

Covers:
- TC-UT-08: Candidate generation produces no duplicates within a candidate.
"""

import pytest

from app.services.itinerary_planner import MonteCarloItineraryPlanner
from app.services.itinerary_builder import ItineraryBuilder
from app.services.plan_ranker import HeuristicPlanRanker
from app.schemas.travel import TravelConstraints
from app.schemas.travel import TravelPreferences


@pytest.fixture
def planner():
    return MonteCarloItineraryPlanner(
        itinerary_builder=ItineraryBuilder(),
        plan_ranker=HeuristicPlanRanker(),
        max_iterations=100,
        random_seed=42,
    )

def test_generate_candidates_contains_no_duplicate_pois_within_candidate(
    planner,
    istanbul_pois,
):
    """
    TC-UT-08 — Each generated candidate must contain unique POI IDs.
    No POI may appear more than once within the same candidate.
    """
    constraints = TravelConstraints(
        max_trip_days=3,
        max_pois_per_day=9,
        max_daily_distance=100_000,
    )

    candidates = planner.generate_candidates(istanbul_pois, constraints)

    assert len(candidates) > 0

    for candidate in candidates:
        poi_ids = [poi.id for poi in candidate]
        assert len(poi_ids) == len(set(poi_ids))



def test_score_is_deterministic_for_identical_inputs(planner, istanbul_pois):
    """
    TC-UT-09 — The score function must be deterministic.
    The same candidate, constraints, and preferences must always produce the same score.
    """
    constraints = TravelConstraints(
        max_trip_days=3,
        max_pois_per_day=9,
        max_daily_distance=100_000,
    )

    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=3,
        categories=["Museum", "Religious"],
        max_distance_per_day=100_000,
    )

    # Fixed candidate: same POIs, same order, same inputs
    candidate = istanbul_pois[:4]

    score1 = planner._score(candidate, constraints, prefs)
    score2 = planner._score(candidate, constraints, prefs)

    assert score1 == score2

def test_select_best_returns_highest_scoring_candidate(planner, istanbul_pois):
    """
    TC-UT-10 — select_best_from_candidates must return the highest-scoring candidate.
    """

    constraints = TravelConstraints(
        max_trip_days=3,
        max_pois_per_day=9,
        max_daily_distance=100_000,
    )

    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=3,
        categories=["Museum"],
        max_distance_per_day=100_000,
    )

    candidate_a = istanbul_pois[:4]
    candidate_b = istanbul_pois[4:8]
    candidate_c = istanbul_pois[8:12]

    candidates = [candidate_a, candidate_b, candidate_c]

    score_map = {
        id(candidate_a): 10,
        id(candidate_b): 20,
        id(candidate_c): 5,
    }

    def fake_score(candidate, constraints, prefs):
        return (score_map[id(candidate)], candidate)

    planner._score = fake_score

    best = planner.select_best_from_candidates(candidates, constraints, prefs)

    assert best is candidate_b


def test_select_best_does_not_assign_same_poi_to_multiple_days(planner, istanbul_pois):
    """
    TC-UT-12 — No POI may be assigned to more than one day in the final itinerary.
    """
    constraints = TravelConstraints(
        max_trip_days=3,
        max_pois_per_day=4,
        max_daily_distance=100_000,
    )

    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=3,
        categories=["Museum", "Religious"],
        max_distance_per_day=100_000,
    )

    itinerary = planner.select_best(istanbul_pois, constraints, prefs)

    all_poi_ids = [
        poi.id
        for day in itinerary.days
        for poi in day.pois
    ]

    assert len(all_poi_ids) == len(set(all_poi_ids))