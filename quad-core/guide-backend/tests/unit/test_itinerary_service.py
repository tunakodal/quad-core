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

class StubPoiRepository:
    async def find_by_id(self, poi_id: str) -> Poi | None:
        return None


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

    service = ItineraryService(
        planner=StubPlanner(),
        poi_repository=StubPoiRepository(),
    )

    new_itinerary, warnings = await service.replan(
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

    service = ItineraryService(
        planner=StubPlanner(),
        poi_repository=StubPoiRepository(),
    )

    constraints = TravelConstraints()
    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=1,
        categories=["Test"],
        max_distance_per_day=100_000,
    )

    replanned, warnings = await service.replan(
        existing=existing,
        edits=edits,
        constraints=constraints,
        prefs=prefs,
    )

    reordered_ids = [poi.id for poi in replanned.days[0].pois]

    assert reordered_ids == ["p2", "p1", "p3"]


@pytest.mark.asyncio
async def test_replan_respects_selected_poi_ids():
    """
    TC-UT-19 — Replan must respect selected POIs from frontend.
    """

    p1 = make_poi("p1")
    p2 = make_poi("p2")
    p3 = make_poi("p3")

    existing = Itinerary(days=[
        DayPlan(day_index=1, pois=[p1, p2, p3]),
    ])

    edits = UserEdits(
        selected_poi_ids=["p1", "p3"]  # 🔥 p2 removed implicitly
    )

    service = ItineraryService(
        planner=StubPlanner(),
        poi_repository=StubPoiRepository(),
    )

    constraints = TravelConstraints()
    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=1,
        categories=["Test"],
        max_distance_per_day=100_000,
    )

    replanned, warnings = await service.replan(
        existing,
        edits,
        constraints,
        prefs,
    )

    ids = [poi.id for poi in replanned.days[0].pois]

    assert set(ids) == {"p1", "p3"}

@pytest.mark.asyncio
async def test_replan_does_not_modify_unaffected_days():
    """
    TC-UT-20 — Edits applied to one day must not affect other days.
    """

    # day 1
    p1 = make_poi("p1")
    p2 = make_poi("p2")

    # day 2
    p3 = make_poi("p3")
    p4 = make_poi("p4")

    existing = Itinerary(days=[
        DayPlan(day_index=1, pois=[p1, p2]),
        DayPlan(day_index=2, pois=[p3, p4]),
    ])

    edits = UserEdits(
        ordered_poi_ids_by_day={
            1: ["p2", "p1"]  # only day 1 changed
        }
    )

    service = ItineraryService(
        planner=StubPlanner(),
        poi_repository=StubPoiRepository(),
    )

    constraints = TravelConstraints()
    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=2,
        categories=["Test"],
        max_distance_per_day=100_000,
    )

    replanned, warnings = await service.replan(
        existing,
        edits,
        constraints,
        prefs,
    )

    # Day 1 changed
    day1_ids = [poi.id for poi in replanned.days[0].pois]
    assert day1_ids == ["p2", "p1"]

    # Day 2 MUST remain identical
    day2_ids = [poi.id for poi in replanned.days[1].pois]
    assert day2_ids == ["p3", "p4"]


@pytest.mark.asyncio
async def test_replan_preserves_valid_day_structure_and_no_duplicates():
    """
    TC-UT-22 — Mixed edits must preserve a valid day structure
    and must not introduce duplicate POIs across days.
    """

    p1 = make_poi("p1")
    p2 = make_poi("p2")
    p3 = make_poi("p3")
    p4 = make_poi("p4")

    existing = Itinerary(days=[
        DayPlan(day_index=1, pois=[p1, p2]),
        DayPlan(day_index=2, pois=[p3, p4]),
    ])

    edits = UserEdits(
        ordered_poi_ids_by_day={
            1: ["p2", "p1"],
            2: ["p4", "p3"],
        }
    )

    service = ItineraryService(
        planner=StubPlanner(),
        poi_repository=StubPoiRepository(),
    )

    constraints = TravelConstraints()
    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=2,
        categories=["Test"],
        max_distance_per_day=100_000,
    )

    replanned, warnings = await service.replan(
        existing,
        edits,
        constraints,
        prefs,
    )

    # valid day structure
    assert len(replanned.days) == 2
    assert [day.day_index for day in replanned.days] == [1, 2]

    # no duplicates across days
    all_ids = [
        poi.id
        for day in replanned.days
        for poi in day.pois
    ]
    assert len(all_ids) == len(set(all_ids))


@pytest.mark.asyncio
async def test_replan_rejects_unknown_poi_id():
    """
    TC-UT-23 — Replanning must reject edits that reference
    a non-existent POI id.
    """

    p1 = make_poi("p1")
    p2 = make_poi("p2")

    existing = Itinerary(days=[
        DayPlan(day_index=1, pois=[p1, p2]),
    ])

    edits = UserEdits(
        ordered_poi_ids_by_day={
            1: ["p1", "p999"]
        }
    )

    service = ItineraryService(
        planner=StubPlanner(),
        poi_repository=StubPoiRepository(),
    )

    constraints = TravelConstraints()
    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=1,
        categories=["Test"],
        max_distance_per_day=100_000,
    )

    with pytest.raises(ValueError) as exc_info:
        await service.replan(
            existing,
            edits,
            constraints,
            prefs,
        )

    assert "p999" in str(exc_info.value)