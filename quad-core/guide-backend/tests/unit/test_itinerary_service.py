import pytest

from app.services.itinerary_service import ItineraryService
from app.models.domain import Itinerary, DayPlan, Poi, GeoPoint
from app.schemas.travel import TravelConstraints, TravelPreferences
from app.schemas.route_dtos import UserEdits
from app.schemas.route_dtos import DayReorderOperation

class StubPlanner:
    def select_best(self, pois, constraints, prefs):
        return Itinerary(days=[
            DayPlan(day_index=1, pois=pois)
        ])


@pytest.fixture
def service():
    return ItineraryService(planner=StubPlanner())


def make_poi(pid):
    return Poi(
        id=pid,
        name=f"POI {pid}",
        category="Test",
        main_category_1="Test",
        main_category_2=None,
        sub_category_1="Test",
        sub_category_2=None,
        sub_category_3=None,
        sub_category_4=None,
        city="Istanbul",
        location=GeoPoint(latitude=41.0, longitude=28.9),
        estimated_visit_duration=60,
        google_rating=None,
        google_reviews_total=None,
    )


@pytest.mark.asyncio
async def test_replan_remove_pois():
    """
    TC-UT-17 — Removed POIs must not appear in the new itinerary.
    """

    existing = Itinerary(days=[
        DayPlan(day_index=1, pois=[make_poi("p1"), make_poi("p2")]),
        DayPlan(day_index=2, pois=[make_poi("p3"), make_poi("p4")]),
    ])

    edits = UserEdits(
        removed_poi_ids=["p2", "p3"]
    )

    constraints = TravelConstraints()
    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=2,
        categories=["Test"],
        max_distance_per_day=100_000,
    )

    service = ItineraryService(planner=StubPlanner())

    new_itinerary = await service.replan(
        existing,
        edits,
        constraints,
        prefs
    )

    remaining_ids = {
        poi.id
        for day in new_itinerary.days
        for poi in day.pois
    }

    assert "p2" not in remaining_ids
    assert "p3" not in remaining_ids


@pytest.mark.asyncio
async def test_replan_reorders_pois_within_a_day():
    """
    TC-UT-18

    Verifies that the replanning result preserves the expected intra-day POI order.
    """

    p1 = make_poi("p1")
    p2 = make_poi("p2")
    p3 = make_poi("p3")

    existing = Itinerary(days=[
        DayPlan(day_index=1, pois=[p1, p2, p3]),
    ])

    edits = UserEdits(
        reorder_operations=[
            DayReorderOperation(
                day_index=1,
                ordered_poi_ids=["p2", "p1", "p3"],
            )
        ]
    )

    service = ItineraryService(planner=StubPlanner())

    constraints = TravelConstraints()
    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=1,
        categories=["Test"],
        max_distance_per_day=100_000,
    )

    replanned = await service.replan(
        existing=existing,
        edits=edits,
        constraints=constraints,
        prefs=prefs,
    )

    reordered_ids = [poi.id for poi in replanned.days[0].pois]

    assert reordered_ids == ["p2", "p1", "p3"]