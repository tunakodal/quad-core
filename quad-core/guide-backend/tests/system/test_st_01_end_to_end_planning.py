import pytest
from fastapi.testclient import TestClient

from app.core.containers import create_container
from main import app



@pytest.mark.asyncio
async def test_end_to_end_planning_produces_usable_multi_day_route_plan():
    """
    ST-01 — Scenario 1: end-to-end planning produces a usable multi-day route plan.

    Scenario:
    - City: Mersin
    - Requested trip duration: 3 days
    - Category count: between 3 and 5
    - No explicit distance preference beyond the required request field

    Expectations:
    - A full end-to-end response is returned successfully
    - The itinerary contains the requested number of days
    - A route plan is returned and remains usable for UI map rendering
    """

    container = await create_container()
    app.state.container = container

    # Derive a stable set of 3–5 categories from the real Mersin dataset.
    mersin_pois = await container.poi_repository.find_by_city("Mersin")

    assert len(mersin_pois) >= 40

    discovered_categories: list[str] = []
    seen: set[str] = set()

    for poi in mersin_pois:
        for category in [
            poi.sub_category_1,
            poi.sub_category_2,
            poi.sub_category_3,
            poi.sub_category_4,
        ]:
            if category and category not in seen:
                seen.add(category)
                discovered_categories.append(category)
            if len(discovered_categories) == 5:
                break
        if len(discovered_categories) == 5:
            break

    selected_categories = discovered_categories[:3]

    assert len(selected_categories) >= 3

    payload = {
        "preferences": {
            "city": "Mersin",
            "trip_days": 3,
            "categories": selected_categories,
            "max_distance_per_day": 100000,
        },
        "constraints": {
            "max_trip_days": 3,
            "max_pois_per_day": 9,
            "max_daily_distance": 100000,
        },
        "language": "EN",
    }

    with TestClient(app) as client:
        response = client.post("/api/v1/routes/generate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "itinerary" in data
    assert "route_plan" in data
    assert "effective_trip_days" in data

    itinerary = data["itinerary"]
    route_plan = data["route_plan"]

    assert "days" in itinerary
    assert isinstance(itinerary["days"], list)
    assert len(itinerary["days"]) == 3
    assert data["effective_trip_days"] == 3

    for day in itinerary["days"]:
        assert "day_index" in day
        assert "pois" in day
        assert isinstance(day["pois"], list)

    assert "segments" in route_plan
    assert "total_distance" in route_plan
    assert "total_duration" in route_plan

    assert isinstance(route_plan["segments"], list)
    assert len(route_plan["segments"]) > 0
    assert route_plan["total_distance"] >= 0
    assert route_plan["total_duration"] >= 0

    for segment in route_plan["segments"]:
        assert "day_index" in segment
        assert "distance" in segment
        assert "duration" in segment
        assert "geometry_encoded" in segment

        assert segment["distance"] >= 0
        assert segment["duration"] >= 0
        assert segment["geometry_encoded"] != ""

