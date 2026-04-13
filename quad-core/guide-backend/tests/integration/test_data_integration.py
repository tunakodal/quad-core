import pytest

from app.core.containers import create_container
from app.schemas.travel import TravelPreferences, TravelConstraints


@pytest.mark.asyncio
async def test_real_dataset_retrieval_returns_valid_domain_entities():
    """
    IT-08 — Core → Data: real dataset retrieval returns consistent domain
    entities without contract violations.

    Scenario:
    - A valid city (Istanbul) and category subset are provided.

    Expectations:
    - POIs are retrieved from the real data source.
    - Each POI contains required domain fields:
        * id
        * category information
        * location with latitude and longitude
    - No null critical fields are present.
    - Core-level retrieval proceeds without contract/runtime errors.
    """

    container = await create_container()

    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=1,
        categories=["Museum"],
        max_distance_per_day=10000,
    )

    pois = await container.poi_service.get_candidate_pois(prefs)

    assert isinstance(pois, list)
    assert len(pois) > 0

    for poi in pois:
        assert poi.id is not None
        assert poi.id != ""

        assert poi.city == "Istanbul"

        assert poi.category is not None
        assert poi.category != ""

        assert poi.location is not None
        assert poi.location.latitude is not None
        assert poi.location.longitude is not None

        assert -90 <= poi.location.latitude <= 90
        assert -180 <= poi.location.longitude <= 180


@pytest.mark.asyncio
async def test_category_mapping_mismatch_is_detectable():
    """
    IT-09 — Core → Data: category mapping mismatches must be detectable.

    Scenario:
    - A category value that does not exist in the dataset is provided.

    Expectations:
    - System does NOT silently return a valid itinerary
    - Either:
        * empty POI result is returned (explicitly detectable), OR
        * a warning/error is produced indicating mismatch
    - No silent failure
    """

    container = await create_container()

    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=1,
        categories=["THIS_CATEGORY_DOES_NOT_EXIST"],
        max_distance_per_day=10000,
    )

    pois = await container.poi_service.get_candidate_pois(prefs)

    assert isinstance(pois, list)

    assert len(pois) == 0

import pytest

from app.core.containers import create_container
from app.schemas.travel import TravelPreferences, TravelConstraints


@pytest.mark.asyncio
async def test_missing_optional_content_does_not_break_planning_pipeline():
    """
    IT-10 — Core → Data: partial or missing optional content must not break
    the planning pipeline.

    Scenario:
    - A valid city/category combination is used
    - Some POIs may lack optional content such as image/audio assets

    Expectations:
    - Candidate POIs are retrieved successfully
    - Itinerary construction completes without crashing
    - Missing optional content does not break the planning flow
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

    itinerary, warnings = await container.itinerary_service.build_itinerary(
        pois,
        constraints,
        prefs,
    )

    assert itinerary is not None
    assert hasattr(itinerary, "days")
    assert isinstance(itinerary.days, list)
    assert len(itinerary.days) > 0

    for day in itinerary.days:
        assert day.day_index is not None
        assert isinstance(day.pois, list)

        for poi in day.pois:
            assert poi.id is not None
            assert poi.category is not None
            assert poi.location is not None
            assert poi.location.latitude is not None
            assert poi.location.longitude is not None