import pytest
from app.services.routing_service import RoutingService, RouteAssembler
from app.integration.osrm_client import OsrmRouteResponse
from app.models.domain import Itinerary, DayPlan, Poi, GeoPoint
from app.schemas.travel import TravelConstraints


class StubOsrmClient:
    async def trip(self, waypoints, profile=None):
        return OsrmRouteResponse(
            distance=1000,
            duration=300,
            geometry_encoded="encoded"
        )


@pytest.fixture
def routing_service():
    return RoutingService(
        osrm_client=StubOsrmClient(),
        route_assembler=RouteAssembler(),
    )


def make_poi(pid, lat):
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
        location=GeoPoint(latitude=lat, longitude=28.9),
        estimated_visit_duration=60,
        google_rating=None,
        google_reviews_total=None,
    )


@pytest.mark.asyncio
async def test_route_segments_are_mapped_to_correct_days(routing_service):
    """
    TC-UT-15 — Route segments must match correct itinerary days.
    """

    itinerary = Itinerary(days=[
        DayPlan(day_index=1, pois=[make_poi("p1", 41.0), make_poi("p2", 41.1)]),
        DayPlan(day_index=2, pois=[make_poi("p3", 41.2), make_poi("p4", 41.3)]),
    ])

    constraints = TravelConstraints()

    route_plan = await routing_service.generate_route(itinerary, constraints)

    # segment sayısı = gün sayısı
    assert len(route_plan.segments) == len(itinerary.days)

    # mapping kontrolü
    for i, segment in enumerate(route_plan.segments):
        assert segment.day_index == itinerary.days[i].day_index

@pytest.mark.asyncio
async def test_route_plan_totals_equal_sum_of_segments(routing_service):
    """
    TC-UT-16 — RoutePlan totals must equal the sum of per-segment values.
    """
    itinerary = Itinerary(days=[
        DayPlan(day_index=1, pois=[make_poi("p1", 41.0), make_poi("p2", 41.1)]),
        DayPlan(day_index=2, pois=[make_poi("p3", 41.2), make_poi("p4", 41.3)]),
    ])

    constraints = TravelConstraints()

    route_plan = await routing_service.generate_route(itinerary, constraints)

    segment_distance_sum = sum(seg.distance for seg in route_plan.segments)
    segment_duration_sum = sum(seg.duration for seg in route_plan.segments)

    assert route_plan.total_distance == segment_distance_sum
    assert route_plan.total_duration == segment_duration_sum