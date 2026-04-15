"""
Unit tests for RequestValidator.
Covers TC-UT-01 through TC-UT-05 from the GUIDE Test Plan.

All tests are synchronous and require no external dependencies.
"""
import pytest
from pydantic import ValidationError

from app.api.validator import RequestValidator
from app.core.config import settings
from app.models.domain import Itinerary, DayPlan, Poi, GeoPoint
from app.schemas.dtos import (
    DayReorderOperation,
    PoiQuery,
    ReplanRequest,
    RouteRequest,
    TravelConstraints,
    TravelPreferences,
    TripDaySuggestionRequest,
    UserEdits,
)
from app.models.enums import  Language

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_route_request(
    city: str = "Istanbul",
    trip_days: int = 3,
    categories: list[str] | None = None,
    max_distance_per_day: int = 50_000,
) -> RouteRequest:
    if categories is None:
        categories = ["Museum"]
    return RouteRequest(
        preferences=TravelPreferences(
            city=city,
            trip_days=trip_days,
            categories=categories,
            max_distance_per_day=max_distance_per_day,
        ),
        constraints=TravelConstraints(),
        language=Language.EN,
    )


def _make_minimal_itinerary() -> Itinerary:
    poi = Poi(
        id="p1",
        name="Test POI",
        category="Cultural Heritage",
        main_category_1="Cultural Heritage",
        main_category_2=None,
        sub_category_1="Religious",
        sub_category_2=None,
        sub_category_3=None,
        sub_category_4=None,
        city="Istanbul",
        location=GeoPoint(latitude=41.0, longitude=28.9),
        estimated_visit_duration=60,
        google_rating=None,
        google_reviews_total=None,
    )
    return Itinerary(days=[DayPlan(day_index=1, pois=[poi])])


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def validator() -> RequestValidator:
    return RequestValidator()


# ── TC-UT-01: Missing city is rejected ────────────────────────────────────────

def test_reject_empty_city(validator):
    """TC-UT-01 — city="" must produce valid=False with a city-related error."""
    req = _make_route_request(city="")
    result = validator.validate_route_request(req)

    assert not result.is_valid
    assert any("city" in e.lower() for e in result.errors)


# ── TC-UT-02: Empty categories must be rejected ──────────────────────────────
# Category selection is mandatory according to the test plan.
# An empty category list must result in valid=False.
def test_reject_empty_categories(validator):
    req = _make_route_request(categories=[])
    result = validator.validate_route_request(req)

    assert not result.is_valid
    assert any("categor" in e.lower() for e in result.errors)

# ── TC-UT-03: At least one planning constraint must be provided ──────────────
# The request must include at least one planning constraint.
# In the current DTO design, missing trip_days and max_distance_per_day
# are rejected at model-construction time by Pydantic.

def test_reject_missing_planning_constraints():
    with pytest.raises(ValidationError) as exc_info:
        RouteRequest(
            preferences=TravelPreferences(
                city="Istanbul",
                trip_days=None,
                categories=["Museum"],
                max_distance_per_day=None,
            ),
            constraints=TravelConstraints(),
            language=Language.EN,
        )

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("trip_days",) for e in errors)
    assert any(e["loc"] == ("max_distance_per_day",) for e in errors)

# ── TC-UT-04: trip_days upper bound ───────────────────────────────────────────
# NOTE: TravelPreferences DTO enforces the upper bound via Pydantic field
# constraints (le=max_trip_days). The rejection therefore happens at the DTO
# construction level before RequestValidator is even called — which is a
# stronger guarantee than post-construction validation.

def test_reject_trip_days_above_max(validator):
    """TC-UT-04 — trip_days > settings.max_trip_days must be rejected.

    TravelPreferences enforces this via a Pydantic field constraint, so the
    ValidationError is raised when building the request object itself.
    """
    with pytest.raises(ValidationError) as exc_info:
        _make_route_request(trip_days=settings.max_trip_days + 1)

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("trip_days",) for e in errors)


def test_accept_trip_days_at_max(validator):
    """Boundary: trip_days == settings.max_trip_days must be accepted."""
    req = _make_route_request(trip_days=settings.max_trip_days)
    result = validator.validate_route_request(req)

    assert result.is_valid


# ── TC-UT-05 (partial): minimum daily distance ────────────────────────────────
# NOTE: The test plan mentions a *city-based* upper bound. The current validator
# only enforces a global minimum (min_daily_distance_meters from settings).
# City-specific upper bounds are not yet implemented.

def test_reject_daily_distance_below_minimum(validator):
    """TC-UT-05 (partial) — max_distance_per_day below min threshold is rejected.

    TravelPreferences enforces this via a Pydantic field constraint, so the
    ValidationError is raised when building the request object itself.
    """
    too_low = settings.min_daily_distance_meters - 1
    with pytest.raises(ValidationError) as exc_info:
        _make_route_request(max_distance_per_day=too_low)

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("max_distance_per_day",) for e in errors)


def test_reject_daily_distance_above_city_limit(validator):
    validator._get_city_max_distance = lambda city: 100000 if city == "Istanbul" else None
    assert validator._get_city_max_distance("Istanbul") == 100000
    req = _make_route_request(
        city="Istanbul",
        max_distance_per_day=100001,
    )
    result = validator.validate_route_request(req)

    assert not result.is_valid
    assert any("max_distance_per_day" in e for e in result.errors)

def test_accept_daily_distance_at_minimum(validator):
    """Boundary: exactly at min_daily_distance_meters must be accepted."""
    req = _make_route_request(max_distance_per_day=settings.min_daily_distance_meters)
    result = validator.validate_route_request(req)

    assert result.is_valid

def test_accept_daily_distance_at_city_limit(validator):
    validator._get_city_max_distance = lambda city: 100_000 if city == "Istanbul" else None

    req = _make_route_request(
        city="Istanbul",
        max_distance_per_day=100_000,
    )
    result = validator.validate_route_request(req)

    assert result.is_valid
# ── Additional: max category count ────────────────────────────────────────────

def test_reject_too_many_categories(validator):
    """Exceed settings.max_category_count must be rejected."""
    over_limit = [f"cat_{i}" for i in range(settings.max_category_count + 1)]
    req = _make_route_request(categories=over_limit)
    result = validator.validate_route_request(req)

    assert not result.is_valid
    assert any("categor" in e.lower() for e in result.errors)


def test_accept_categories_at_max_count(validator):
    """Boundary: exactly max_category_count categories must be accepted."""
    at_limit = [f"cat_{i}" for i in range(settings.max_category_count)]
    req = _make_route_request(categories=at_limit)
    result = validator.validate_route_request(req)

    assert result.is_valid


# ── Additional: fully valid request ───────────────────────────────────────────

def test_valid_route_request_passes(validator):
    """A well-formed RouteRequest with all fields valid must pass."""
    req = _make_route_request()
    result = validator.validate_route_request(req)

    assert result.is_valid
    assert result.errors == []


# ── ReplanRequest validation ───────────────────────────────────────────────────

def test_replan_rejects_empty_itinerary(validator):
    """ReplanRequest with zero days must be rejected."""
    req = ReplanRequest(
        existing_itinerary=Itinerary(days=[]),
        edits=UserEdits(),
        constraints=TravelConstraints(),
    )
    result = validator.validate_replan_request(req)

    assert not result.is_valid


def test_replan_rejects_unknown_day_index_in_ordered_poi_ids_by_day(validator):
    """ordered_poi_ids_by_day referencing a non-existent day_index must be rejected."""
    itinerary = _make_minimal_itinerary()
    edits = UserEdits(
        ordered_poi_ids_by_day={99: ["p1"]}
    )
    req = ReplanRequest(
        existing_itinerary=itinerary,
        edits=edits,
        constraints=TravelConstraints(),
    )
    result = validator.validate_replan_request(req)

    assert not result.is_valid
    assert any("unknown day_index 99" in e.lower() for e in result.errors)


def test_replan_valid_request_passes(validator):
    """A valid ReplanRequest with an existing itinerary must pass."""
    itinerary = _make_minimal_itinerary()
    req = ReplanRequest(
        existing_itinerary=itinerary,
        edits=UserEdits(),
        constraints=TravelConstraints(),
    )
    result = validator.validate_replan_request(req)

    assert result.is_valid


# ── PoiQuery validation ────────────────────────────────────────────────────────

def test_poi_query_rejects_missing_city(validator):
    query = PoiQuery(city="")
    result = validator.validate_poi_query(query)

    assert not result.is_valid
    assert any("city" in e.lower() for e in result.errors)


def test_poi_query_valid(validator):
    query = PoiQuery(city="Istanbul", categories=["Museum"])
    result = validator.validate_poi_query(query)

    assert result.is_valid


def test_poi_query_rejects_too_many_categories(validator):
    over_limit = [f"cat_{i}" for i in range(settings.max_category_count + 1)]
    query = PoiQuery(city="Istanbul", categories=over_limit)
    result = validator.validate_poi_query(query)

    assert not result.is_valid


# ── TripDaySuggestionRequest validation ───────────────────────────────────────

def test_trip_day_suggestion_rejects_missing_city(validator):
    req = TripDaySuggestionRequest(city="")
    result = validator.validate_trip_day_suggestion_request(req)

    assert not result.is_valid


def test_trip_day_suggestion_valid(validator):
    req = TripDaySuggestionRequest(city="Istanbul")
    result = validator.validate_trip_day_suggestion_request(req)

    assert result.is_valid

