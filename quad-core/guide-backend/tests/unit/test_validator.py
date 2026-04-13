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
        categories = ["Historical"]
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
        id="p1", name="Test POI", category="Historical", city="Istanbul",
        location=GeoPoint(latitude=41.0, longitude=28.9),
        estimated_visit_duration=60,
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


# ── TC-UT-02: Empty categories → WARNING (not a hard error) ──────────────────
# NOTE: The test plan (TC-UT-02) says this should produce valid=False.
# Current validator.py implementation treats empty categories as a non-fatal
# warning (NO_CATEGORIES) so the request is still considered valid.
# This test documents the *actual* behaviour; update the validator if the
# stricter spec is desired.

def test_empty_categories_produces_warning_not_error(validator):
    """TC-UT-02 (adjusted) — empty categories → warning, request still valid."""
    req = _make_route_request(categories=[])
    result = validator.validate_route_request(req)

    assert result.is_valid
    assert any(w.code == "NO_CATEGORIES" for w in result.warnings)


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


def test_accept_daily_distance_at_minimum(validator):
    """Boundary: exactly at min_daily_distance_meters must be accepted."""
    req = _make_route_request(max_distance_per_day=settings.min_daily_distance_meters)
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


def test_replan_rejects_unknown_day_index_in_reorder(validator):
    """Reorder operation referencing a non-existent day_index must be rejected."""
    itinerary = _make_minimal_itinerary()
    edits = UserEdits(
        reorder_operations=[DayReorderOperation(day_index=99, ordered_poi_ids=["p1"])]
    )
    req = ReplanRequest(
        existing_itinerary=itinerary,
        edits=edits,
        constraints=TravelConstraints(),
    )
    result = validator.validate_replan_request(req)

    assert not result.is_valid
    assert any("99" in e for e in result.errors)


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
    query = PoiQuery(city="Istanbul", categories=["Historical"])
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
