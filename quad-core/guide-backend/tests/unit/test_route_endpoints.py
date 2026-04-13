
import pytest

from app.api.routes.route_endpoints import RouteController
from app.api.validator import RequestValidator
from app.models.domain import Itinerary, DayPlan, Poi, GeoPoint
from app.models.route import RoutePlan, RouteSegment
from app.schemas.route_dtos import RouteRequest
from app.schemas.travel import TravelConstraints, TravelPreferences
from app.models.enums import Language
from app.schemas.suggestion_dtos import TripDaySuggestionRequest

"""
Unit tests for RouteController.

Covers:
- TC-UT-11: System returns insufficiency guidance through trip-day suggestion.
"""

class StubPoiServiceForSuggestion:
    def __init__(self, count: int):
        self._count = count

    async def count_available_pois(self, city: str, categories: list[str]) -> int:
        return self._count

class DummyItineraryService:
    pass


class DummyRoutingService:
    pass


@pytest.mark.asyncio
async def test_suggest_trip_days_returns_reduced_day_recommendation_for_small_poi_pool():
    """
    TC-UT-11 — When the eligible POI pool is insufficient for the requested duration,
    the system should return guidance via max_recommended_days.
    """
    controller = RouteController(
        validator=RequestValidator(),
        poi_service=StubPoiServiceForSuggestion(count=11),
        itinerary_service=DummyItineraryService(),
        routing_service=DummyRoutingService(),
    )

    req = TripDaySuggestionRequest(
        city="Yalova",
        categories=["Museum", "Religious"],
    )

    result = await controller.suggest_trip_days(req)

    assert result.poi_count == 11
    assert result.max_recommended_days == 2


class StubPoiServiceForGenerate:
    async def get_candidate_pois(self, prefs):
        return [
            Poi(
                id="p1",
                name="Museum A",
                category="Museums",
                main_category_1="Museums",
                main_category_2=None,
                sub_category_1="Museum",
                sub_category_2=None,
                sub_category_3=None,
                sub_category_4=None,
                city="Istanbul",
                location=GeoPoint(latitude=41.0082, longitude=28.9784),
                estimated_visit_duration=90,
                google_rating=4.5,
                google_reviews_total=1000,
            ),
            Poi(
                id="p2",
                name="Mosque B",
                category="Cultural Heritage",
                main_category_1="Cultural Heritage",
                main_category_2=None,
                sub_category_1="Religious",
                sub_category_2=None,
                sub_category_3=None,
                sub_category_4=None,
                city="Istanbul",
                location=GeoPoint(latitude=41.0133, longitude=28.9843),
                estimated_visit_duration=60,
                google_rating=4.6,
                google_reviews_total=800,
            ),
        ]


class StubItineraryService:
    async def build_itinerary(self, pois, constraints, prefs):
        return (
            Itinerary(
                days=[
                    DayPlan(day_index=1, pois=pois)
                ]
            ),
            [],
        )


class StubRoutingService:
    async def generate_route(self, itinerary, constraints):
        return (
            RoutePlan(
                segments=[
                    RouteSegment(
                        day_index=1,
                        distance=5000,
                        duration=900,
                        geometry_encoded="encoded_polyline_here",
                    )
                ],
                total_distance=5000,
                total_duration=900,
                geometry_encoded="encoded_polyline_here",
            ),
            [],
        )

@pytest.mark.asyncio
async def test_generate_route_final_output_satisfies_request_constraints():
    """
    TC-UT-14 — Final routed output must remain consistent with the request:
    correct day count, city, selected categories, and non-empty route structure.
    """
    controller = RouteController(
        validator=RequestValidator(),
        poi_service=StubPoiServiceForGenerate(),
        itinerary_service=StubItineraryService(),
        routing_service=StubRoutingService(),
    )

    req = RouteRequest(
        preferences=TravelPreferences(
            city="Istanbul",
            trip_days=1,
            categories=["Museum", "Religious"],
            max_distance_per_day=100_000,
        ),
        constraints=TravelConstraints(
            max_trip_days=1,
            max_pois_per_day=9,
            max_daily_distance=100_000,
        ),
        language=Language.EN,
    )

    response = await controller.generate_route(req)

    # (i) effective trip days match requested trip days
    assert len(response.itinerary.days) == req.preferences.trip_days
    assert response.effective_trip_days == req.preferences.trip_days

    # (ii) all POIs belong to the requested city
    all_pois = [poi for day in response.itinerary.days for poi in day.pois]
    assert all(poi.city == req.preferences.city for poi in all_pois)

    # (iii) all POIs match at least one selected category (subcategory-based truth source)
    selected = set(req.preferences.categories)
    assert all(
        any(
            c in selected
            for c in [
                poi.sub_category_1,
                poi.sub_category_2,
                poi.sub_category_3,
                poi.sub_category_4,
            ]
            if c
        )
        for poi in all_pois
    )

    # (iv) route structure remains well formed
    assert response.route_plan is not None
    assert hasattr(response.route_plan, "segments")
    assert isinstance(response.route_plan.segments, list)
    assert response.route_plan.total_distance >= 0
    assert response.route_plan.total_duration >= 0