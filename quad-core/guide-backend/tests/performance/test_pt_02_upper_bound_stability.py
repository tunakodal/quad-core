import time

import pytest
from fastapi.testclient import TestClient

from app.core.containers import create_container
from main import app


@pytest.mark.asyncio
async def test_upper_bound_configuration_does_not_cause_instability():
    """
    PT-02 — Upper-bound configuration does not cause instability.

    Scenario:
    - Maximum trip days
    - Maximum category count
    - Large pool city
    - Real system execution (no mocks)

    Expectations:
    - System completes without crash or timeout
    - End-to-end latency remains bounded under upper-bound workload
    """

    container = await create_container()
    app.state.container = container

    istanbul_pois = await container.poi_repository.find_by_city("Istanbul")
    assert len(istanbul_pois) > 0

    discovered_categories: list[str] = []
    seen: set[str] = set()

    for poi in istanbul_pois:
        for category in [
            poi.sub_category_1,
            poi.sub_category_2,
            poi.sub_category_3,
            poi.sub_category_4,
        ]:
            if category and category not in seen:
                seen.add(category)
                discovered_categories.append(category)
            if len(discovered_categories) == 10:
                break
        if len(discovered_categories) == 10:
            break

    selected_categories = discovered_categories[:10]
    assert len(selected_categories) >= 5

    payload = {
        "preferences": {
            "city": "Istanbul",
            "trip_days": 7,
            "categories": selected_categories,
            "max_distance_per_day": 100000,
        },
        "constraints": {
            "max_trip_days": 7,
            "max_pois_per_day": 9,
            "max_daily_distance": 100000,
        },
        "language": "EN",
    }

    with TestClient(app) as client:
        start = time.perf_counter()
        response = client.post("/api/v1/routes/generate", json=payload)
        elapsed = time.perf_counter() - start

    assert response.status_code == 200, (
        f"Upper-bound planning failed. "
        f"Status={response.status_code}, Body={response.text}"
    )

    data = response.json()

    assert "itinerary" in data
    assert "route_plan" in data
    assert "effective_trip_days" in data

    itinerary = data["itinerary"]
    route_plan = data["route_plan"]

    assert isinstance(itinerary["days"], list)
    assert len(itinerary["days"]) > 0

    assert isinstance(route_plan["segments"], list)
    assert len(route_plan["segments"]) > 0

    for segment in route_plan["segments"]:
        assert "day_index" in segment
        assert "distance" in segment
        assert "duration" in segment
        assert "geometry_encoded" in segment
        assert segment["distance"] >= 0
        assert segment["duration"] >= 0
        assert segment["geometry_encoded"] != ""

    assert elapsed <= 10.0, (
        f"Upper-bound latency appears unbounded. "
        f"Elapsed={elapsed:.3f}s"
    )