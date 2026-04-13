from fastapi.testclient import TestClient

import pytest
import httpx

from main import app
from app.models.domain import Itinerary, DayPlan, Poi, GeoPoint
from app.models.route import RoutePlan
from app.schemas.common import ValidationResult
from app.api.validator import RequestValidator
from app.core.containers import create_container
from app.schemas.travel import TravelPreferences, TravelConstraints




class StubValidator:
    def validate_route_request(self, req):
        return ValidationResult(is_valid=True, errors=[], warnings=[])

    def validate_replan_request(self, req):
        return ValidationResult(is_valid=True, errors=[], warnings=[])

    def validate_trip_day_suggestion_request(self, req):
        return ValidationResult(is_valid=True, errors=[], warnings=[])


class SpyPoiService:
    def __init__(self):
        self.last_prefs = None

    async def get_candidate_pois(self, prefs):
        self.last_prefs = prefs
        return [
            Poi(
                id="p1",
                name="Test Museum",
                category="Museums",
                main_category_1="Museums",
                main_category_2=None,
                sub_category_1="Museum",
                sub_category_2=None,
                sub_category_3=None,
                sub_category_4=None,
                city=prefs.city,
                location=GeoPoint(latitude=41.0082, longitude=28.9784),
                estimated_visit_duration=60,
                google_rating=None,
                google_reviews_total=None,
            ),
            Poi(
                id="p2",
                name="Test Mosque",
                category="Cultural Heritage",
                main_category_1="Cultural Heritage",
                main_category_2=None,
                sub_category_1="Religious",
                sub_category_2=None,
                sub_category_3=None,
                sub_category_4=None,
                city=prefs.city,
                location=GeoPoint(latitude=41.0133, longitude=28.9843),
                estimated_visit_duration=60,
                google_rating=None,
                google_reviews_total=None,
            ),
        ]

    async def count_available_pois(self, city, categories):
        return 2


class SpyItineraryService:
    def __init__(self):
        self.last_prefs = None
        self.last_constraints = None

    async def build_itinerary(self, pois, constraints, prefs):
        self.last_prefs = prefs
        self.last_constraints = constraints
        return (
            Itinerary(days=[DayPlan(day_index=1, pois=pois)]),
            [],
        )


class SpyRoutingService:
    def __init__(self):
        self.last_constraints = None

    async def generate_route(self, itinerary, constraints):
        self.last_constraints = constraints
        return (
            RoutePlan(
                segments=[],
                total_distance=0,
                total_duration=0,
                geometry_encoded="",
            ),
            [],
        )

class StubContainer:
    def __init__(self):
        self.validator = StubValidator()
        self.poi_service = SpyPoiService()
        self.itinerary_service = SpyItineraryService()
        self.routing_service = SpyRoutingService()


def test_route_request_json_maps_correctly_to_backend_dtos():
    """
    IT-01 — Frontend request schema must map correctly to backend DTO fields.
    """
    container = StubContainer()
    app.state.container = container

    client = TestClient(app)

    payload = {
        "preferences": {
            "city": "Istanbul",
            "trip_days": 3,
            "categories": ["Museum", "Religious"],
            "max_distance_per_day": 10000,
        },
        "constraints": {
            "max_trip_days": 3,
            "max_pois_per_day": 9,
            "max_daily_distance": 10000,
        },
        "language": "EN",
    }

    response = client.post("/api/v1/routes/generate", json=payload)

    assert response.status_code == 200

    poi_prefs = container.poi_service.last_prefs
    itin_prefs = container.itinerary_service.last_prefs
    itin_constraints = container.itinerary_service.last_constraints
    routing_constraints = container.routing_service.last_constraints

    assert poi_prefs is not None
    assert itin_prefs is not None
    assert itin_constraints is not None
    assert routing_constraints is not None

    assert poi_prefs.city == "Istanbul"
    assert poi_prefs.trip_days == 3
    assert poi_prefs.categories == ["Museum", "Religious"]
    assert poi_prefs.max_distance_per_day == 10000

    assert itin_prefs.city == "Istanbul"
    assert itin_prefs.trip_days == 3
    assert itin_prefs.categories == ["Museum", "Religious"]
    assert itin_prefs.max_distance_per_day == 10000

    assert itin_constraints.max_trip_days == 3
    assert itin_constraints.max_pois_per_day == 9
    assert itin_constraints.max_daily_distance == 10000

    assert routing_constraints.max_trip_days == 3
    assert routing_constraints.max_pois_per_day == 9
    assert routing_constraints.max_daily_distance == 10000


def test_distance_value_is_forwarded_in_internal_units():
    """
    IT-02 — Distance value provided in internal units must be forwarded
    correctly across the API boundary.
    """

    class TrackingPoiService:
        def __init__(self):
            self.last_prefs = None

        async def get_candidate_pois(self, prefs):
            self.last_prefs = prefs
            return [
                Poi(
                    id="p1",
                    name="Test Museum",
                    category="Museums",
                    main_category_1="Museums",
                    main_category_2=None,
                    sub_category_1="Museum",
                    sub_category_2=None,
                    sub_category_3=None,
                    sub_category_4=None,
                    city=prefs.city,
                    location=GeoPoint(latitude=41.0082, longitude=28.9784),
                    estimated_visit_duration=60,
                    google_rating=None,
                    google_reviews_total=None,
                ),
                Poi(
                    id="p2",
                    name="Test Mosque",
                    category="Cultural Heritage",
                    main_category_1="Cultural Heritage",
                    main_category_2=None,
                    sub_category_1="Religious",
                    sub_category_2=None,
                    sub_category_3=None,
                    sub_category_4=None,
                    city=prefs.city,
                    location=GeoPoint(latitude=41.0133, longitude=28.9843),
                    estimated_visit_duration=60,
                    google_rating=None,
                    google_reviews_total=None,
                ),
            ]

        async def count_available_pois(self, city, categories):
            return 2

    container = StubContainer()
    container.poi_service = TrackingPoiService()
    app.state.container = container

    client = TestClient(app)

    payload = {
        "preferences": {
            "city": "Istanbul",
            "trip_days": 1,
            "categories": ["Museum"],
            "max_distance_per_day": 10000,
        },
        "constraints": {
            "max_trip_days": 1,
            "max_pois_per_day": 5,
            "max_daily_distance": 10000,
        },
        "language": "EN",
    }

    response = client.post("/api/v1/routes/generate", json=payload)

    assert response.status_code == 200

    prefs = container.poi_service.last_prefs
    assert prefs is not None
    assert prefs.max_distance_per_day == 10000


def test_generate_route_returns_stable_error_payload_for_invalid_request():
    """
    IT-03 — Invalid requests must return a stable and parseable error payload.

    Scenario:
    - Missing required field (city)

    Expectations:
    - HTTP 4xx response
    - Response contains a structured error payload
    - Payload is parseable by frontend
    """

    container = StubContainer()
    container.validator = RequestValidator()

    app.state.container = container

    client = TestClient(app)

    payload = {
        "preferences": {
            "city": "",
            "trip_days": 1,
            "categories": ["Museum"],
            "max_distance_per_day": 10000,
        },
        "constraints": {
            "max_trip_days": 1,
            "max_pois_per_day": 5,
            "max_daily_distance": 10000,
        },
        "language": "EN",
    }

    response = client.post("/api/v1/routes/generate", json=payload)

    assert response.status_code == 422

    data = response.json()

    assert isinstance(data, dict)
    assert "message" in data
    assert "error_code" in data
    assert "details" in data

    assert isinstance(data["message"], str)
    assert isinstance(data["error_code"], str)
    assert isinstance(data["details"], list)

    assert data["error_code"] == "VALIDATION_ERROR"
    assert any("city" in str(item).lower() for item in data["details"])


def test_generate_route_returns_stable_warning_payload():
    """
    IT-04 — Non-fatal warnings must be returned in a stable response payload.

    Scenario:
    - The request is valid.
    - Request processing produces a warning.

    Expectations:
    - HTTP 200 response
    - Response includes a warnings field
    - Warning entry is distinguishable from a fatal error and contains
      guidance-related fields
    """

    class WarningValidator:
        def validate_route_request(self, req):
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[
                    {
                        "code": "INSUFFICIENT_POIS",
                        "severity": "WARN",
                        "message": "Available POIs may be insufficient for the requested planning scope.",
                    }
                ],
            )

        def validate_replan_request(self, req):
            return ValidationResult(is_valid=True, errors=[], warnings=[])

        def validate_trip_day_suggestion_request(self, req):
            return ValidationResult(is_valid=True, errors=[], warnings=[])

    container = StubContainer()
    container.validator = WarningValidator()

    app.state.container = container

    client = TestClient(app)

    payload = {
        "preferences": {
            "city": "Istanbul",
            "trip_days": 1,
            "categories": ["Museum"],
            "max_distance_per_day": 10000,
        },
        "constraints": {
            "max_trip_days": 1,
            "max_pois_per_day": 5,
            "max_daily_distance": 10000,
        },
        "language": "EN",
    }

    response = client.post("/api/v1/routes/generate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "warnings" in data
    assert isinstance(data["warnings"], list)
    assert len(data["warnings"]) == 1

    warning = data["warnings"][0]

    assert isinstance(warning, dict)
    assert "code" in warning
    assert "severity" in warning
    assert "message" in warning

    assert warning["code"] == "INSUFFICIENT_POIS"
    assert warning["severity"] == "WARN"
    assert "insufficient" in warning["message"].lower()


def test_controller_invokes_services_in_correct_order_and_returns_complete_response():
    """
    IT-05 — API Boundary → Core: controller must orchestrate the correct
    service invocation chain.

    Scenario:
    - A valid route generation request is sent to the API.

    Expectations:
    - PoiService, ItineraryService, and RoutingService are invoked
      in the correct sequence
    - The response is assembled into a RouteResponse structure
    - No required fields are missing in the final response
    """

    call_order = []

    class TrackingPoiService:
        async def get_candidate_pois(self, prefs):
            call_order.append("poi_service")
            return [
                Poi(
                    id="p1",
                    name="Test POI 1",
                    category="Test",
                    main_category_1="Test",
                    main_category_2=None,
                    sub_category_1="Test",
                    sub_category_2=None,
                    sub_category_3=None,
                    sub_category_4=None,
                    city=prefs.city,
                    location=GeoPoint(latitude=41.0, longitude=28.9),
                    estimated_visit_duration=60,
                    google_rating=None,
                    google_reviews_total=None,
                ),
                Poi(
                    id="p2",
                    name="Test POI 2",
                    category="Test",
                    main_category_1="Test",
                    main_category_2=None,
                    sub_category_1="Test",
                    sub_category_2=None,
                    sub_category_3=None,
                    sub_category_4=None,
                    city=prefs.city,
                    location=GeoPoint(latitude=41.1, longitude=28.9),
                    estimated_visit_duration=60,
                    google_rating=None,
                    google_reviews_total=None,
                ),
            ]

        async def count_available_pois(self, city, categories):
            return 2

    class TrackingItineraryService:
        async def build_itinerary(self, pois, constraints, prefs):
            call_order.append("itinerary_service")
            return (
                Itinerary(days=[DayPlan(day_index=1, pois=pois)]),
                [],
            )

    class TrackingRoutingService:
        async def generate_route(self, itinerary, constraints):
            call_order.append("routing_service")
            return (
                RoutePlan(
                    segments=[],
                    total_distance=0,
                    total_duration=0,
                    geometry_encoded="",
                ),
                [],
            )

    container = type("C", (), {})()
    container.validator = StubValidator()
    container.poi_service = TrackingPoiService()
    container.itinerary_service = TrackingItineraryService()
    container.routing_service = TrackingRoutingService()

    app.state.container = container

    client = TestClient(app)

    payload = {
        "preferences": {
            "city": "Istanbul",
            "trip_days": 1,
            "categories": ["Museum"],
            "max_distance_per_day": 10000,
        },
        "constraints": {
            "max_trip_days": 1,
            "max_pois_per_day": 5,
            "max_daily_distance": 10000,
        },
        "language": "EN",
    }

    response = client.post("/api/v1/routes/generate", json=payload)

    assert response.status_code == 200

    # service invocation order
    assert call_order == [
        "poi_service",
        "itinerary_service",
        "routing_service",
    ]

    data = response.json()

    # response completeness
    assert "itinerary" in data
    assert "route_plan" in data
    assert "effective_trip_days" in data

    assert isinstance(data["itinerary"], dict)
    assert isinstance(data["route_plan"], dict)


def test_validation_failure_blocks_core_service_execution():
    """
    IT-06 — API Boundary → Core: validation failure must prevent
    core service execution.

    Scenario:
    - An invalid request is sent (validation fails).

    Expectations:
    - HTTP 4xx response is returned
    - Core services (PoiService, ItineraryService, RoutingService)
      are NOT invoked
    - Error response follows the defined error payload structure
    """

    class FailingValidator:
        def validate_route_request(self, req):
            return ValidationResult(
                is_valid=False,
                errors=["Invalid request"],
                warnings=[],
            )

    class TrackingPoiService:
        def __init__(self):
            self.called = False

        async def get_candidate_pois(self, prefs):
            self.called = True
            return []

        async def count_available_pois(self, city, categories):
            return 0

    class TrackingItineraryService:
        def __init__(self):
            self.called = False

        async def build_itinerary(self, pois, constraints, prefs):
            self.called = True
            return Itinerary(days=[]), []

    class TrackingRoutingService:
        def __init__(self):
            self.called = False

        async def generate_route(self, itinerary, constraints):
            self.called = True
            return (
                RoutePlan(
                    segments=[],
                    total_distance=0,
                    total_duration=0,
                    geometry_encoded="",
                ),
                [],
            )

    poi_service = TrackingPoiService()
    itinerary_service = TrackingItineraryService()
    routing_service = TrackingRoutingService()

    container = type("C", (), {})()
    container.validator = FailingValidator()
    container.poi_service = poi_service
    container.itinerary_service = itinerary_service
    container.routing_service = routing_service

    app.state.container = container

    client = TestClient(app)

    payload = {
        "preferences": {
            "city": "",  # invalid
            "trip_days": 1,
            "categories": ["Museum"],
            "max_distance_per_day": 10000,
        },
        "constraints": {
            "max_trip_days": 1,
            "max_pois_per_day": 5,
            "max_daily_distance": 10000,
        },
        "language": "EN",
    }

    response = client.post("/api/v1/routes/generate", json=payload)

    # validation must fail
    assert response.status_code == 422

    # core services must NOT be called
    assert poi_service.called is False
    assert itinerary_service.called is False
    assert routing_service.called is False

    # error payload must be consistent
    data = response.json()

    assert "message" in data
    assert "error_code" in data
    assert "details" in data


def test_warning_propagation_from_core_to_api_response():
    """
    IT-07 — API Boundary → Core: warnings produced in core must be
    propagated to the API response without loss.
    """

    class CleanValidator:
        def validate_route_request(self, req):
            return ValidationResult(is_valid=True, errors=[], warnings=[])

        def validate_replan_request(self, req):
            return ValidationResult(is_valid=True, errors=[], warnings=[])

        def validate_trip_day_suggestion_request(self, req):
            return ValidationResult(is_valid=True, errors=[], warnings=[])

    class LimitedPoiService:
        async def get_candidate_pois(self, prefs):
            # deliberately small dataset → PARTIAL_ITINERARY trigger
            return [
                Poi(
                    id="p1",
                    name="Test POI 1",
                    category="Test",
                    main_category_1="Test",
                    main_category_2=None,
                    sub_category_1="Test",
                    sub_category_2=None,
                    sub_category_3=None,
                    sub_category_4=None,
                    city=prefs.city,
                    location=GeoPoint(latitude=41.0, longitude=28.9),
                    estimated_visit_duration=60,
                    google_rating=None,
                    google_reviews_total=None,
                ),
                Poi(
                    id="p2",
                    name="Test POI 2",
                    category="Test",
                    main_category_1="Test",
                    main_category_2=None,
                    sub_category_1="Test",
                    sub_category_2=None,
                    sub_category_3=None,
                    sub_category_4=None,
                    city=prefs.city,
                    location=GeoPoint(latitude=41.1, longitude=28.9),
                    estimated_visit_duration=60,
                    google_rating=None,
                    google_reviews_total=None,
                ),
            ]

        async def count_available_pois(self, city, categories):
            return 2

    class WarningItineraryService:
        async def build_itinerary(self, pois, constraints, prefs):
            return (
                Itinerary(days=[DayPlan(day_index=1, pois=pois)]),
                [
                    {
                        "code": "PARTIAL_ITINERARY",
                        "severity": "WARN",
                        "message": "Requested trip duration could not be fully satisfied with available POIs.",
                    }
                ],
            )

    container = StubContainer()
    container.validator = CleanValidator()
    container.poi_service = LimitedPoiService()
    container.itinerary_service = WarningItineraryService()

    app.state.container = container

    client = TestClient(app)

    payload = {
        "preferences": {
            "city": "Istanbul",
            "trip_days": 3,  # intentionally higher → triggers warning
            "categories": ["Museum"],
            "max_distance_per_day": 10000,
        },
        "constraints": {
            "max_trip_days": 3,
            "max_pois_per_day": 5,
            "max_daily_distance": 10000,
        },
        "language": "EN",
    }

    response = client.post("/api/v1/routes/generate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "warnings" in data
    assert isinstance(data["warnings"], list)
    assert len(data["warnings"]) > 0

    warning = data["warnings"][0]

    assert "code" in warning
    assert "severity" in warning
    assert "message" in warning

    assert warning["code"] == "PARTIAL_ITINERARY"
    assert warning["severity"] == "WARN"
    assert "could not be fully satisfied" in warning["message"].lower()

    # response still usable
    assert "itinerary" in data
    assert "route_plan" in data


@pytest.mark.asyncio
async def test_osrm_returns_geometry_distance_and_duration_for_generated_itinerary():
    """
    IT-11 — Core → OSRM: geometry, distance, and duration must be returned
    and serialized in a frontend-consumable format.

    Scenario:
    - A valid itinerary is generated from real data
    - Routing is computed through the real OSRM integration

    Expectations:
    - RoutePlan is produced successfully
    - At least one route segment exists
    - Each segment contains non-empty geometry plus distance and duration
    - Total distance and total duration are present and non-negative
    """

    container = await create_container()

    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=1,
        categories=["Museum"],
        max_distance_per_day=10000,
    )

    constraints = TravelConstraints(
        max_trip_days=1,
        max_pois_per_day=5,
        max_daily_distance=10000,
    )

    pois = await container.poi_service.get_candidate_pois(prefs)
    assert isinstance(pois, list)
    assert len(pois) >= 2

    itinerary, itinerary_warnings = await container.itinerary_service.build_itinerary(
        pois,
        constraints,
        prefs,
    )

    assert itinerary is not None
    assert len(itinerary.days) > 0

    route_plan, routing_warnings = await container.routing_service.generate_route(
        itinerary,
        constraints,
    )

    assert route_plan is not None
    assert hasattr(route_plan, "segments")
    assert isinstance(route_plan.segments, list)
    assert len(route_plan.segments) > 0

    assert route_plan.total_distance is not None
    assert route_plan.total_duration is not None
    assert route_plan.total_distance >= 0
    assert route_plan.total_duration >= 0

    for segment in route_plan.segments:
        assert segment.day_index is not None
        assert segment.distance is not None
        assert segment.duration is not None
        assert segment.geometry_encoded is not None

        assert segment.distance >= 0
        assert segment.duration >= 0
        assert segment.geometry_encoded != ""

    assert route_plan.geometry_encoded is not None


def test_osrm_failure_returns_stable_error_response():
    """
    IT-12 — Core → OSRM: routing failures must be handled gracefully
    without breaking the API contract.

    Scenario:
    - OSRM fails during route computation

    Expectations:
    - API returns a deterministic failure response
    - Error payload remains stable and parseable
    - No partially corrupted response is returned
    """

    class FailingOsrmClient:
        async def trip(self, waypoints, profile=None):
            raise httpx.ConnectError("OSRM unavailable")

    async def _build_client():
        container = await create_container()
        container.routing_service.osrm_client = FailingOsrmClient()
        app.state.container = container

    import asyncio
    asyncio.run(_build_client())

    client = TestClient(app)

    payload = {
        "preferences": {
            "city": "Istanbul",
            "trip_days": 1,
            "categories": ["Museum"],
            "max_distance_per_day": 10000,
        },
        "constraints": {
            "max_trip_days": 1,
            "max_pois_per_day": 5,
            "max_daily_distance": 10000,
        },
        "language": "EN",
    }

    response = client.post("/api/v1/routes/generate", json=payload)

    assert response.status_code in (500, 502, 503)

    data = response.json()

    assert isinstance(data, dict)
    assert "message" in data
    assert "error_code" in data
    assert "details" in data

    assert isinstance(data["message"], str)
    assert isinstance(data["error_code"], str)
    assert isinstance(data["details"], list)

    assert "osrm" in data["message"].lower() or any(
        "osrm" in str(item).lower() or "routing" in str(item).lower()
        for item in data["details"]
    )

    assert "itinerary" not in data
    assert "route_plan" not in data