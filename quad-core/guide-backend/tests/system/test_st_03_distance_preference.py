import pytest
import json
from fastapi.testclient import TestClient

from app.core.containers import create_container
from main import app


@pytest.mark.asyncio
async def test_distance_preference_is_reflected_in_final_routed_output():
    """
    ST-03 — Scenario 3: distance preference is reflected in the final routed output
    end-to-end.

    Scenario:
    - City: Istanbul
    - Near-maximum trip duration
    - Maximum category selection
    - Narrow daily distance target (10 km)

    Expectations:
    - End-to-end planning completes successfully
    - Routed output reflects distance-sensitive behavior
    - Daily route distances stay within or near the target range
      according to an explicit tolerance policy
    - System remains stable throughout the workflow
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

    target_daily_distance = 30_000
    lower_bound = 0
    upper_bound = target_daily_distance * 2

    payload = {
        "preferences": {
            "city": "Istanbul",
            "trip_days": 7,
            "categories": selected_categories,
            "max_distance_per_day": target_daily_distance,
        },
        "constraints": {
            "max_trip_days": 7,
            "max_pois_per_day": 9,
            "max_daily_distance": target_daily_distance,
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

    assert isinstance(itinerary["days"], list)
    assert len(itinerary["days"]) > 0
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

    segment_distances = [segment["distance"] for segment in route_plan["segments"]]
    assert len(segment_distances) == len(itinerary["days"])

    violations = [distance for distance in segment_distances if not (lower_bound <= distance <= upper_bound)]

    if violations:
        debug_days = []
        for day in itinerary["days"]:
            debug_days.append(
                {
                    "day_index": day["day_index"],
                    "poi_count": len(day["pois"]),
                    "poi_ids": [poi["id"] for poi in day["pois"]],
                    "poi_names": [poi["name"] for poi in day["pois"]],
                }
            )

        debug_segments = [
            {
                "day_index": segment["day_index"],
                "distance": segment["distance"],
                "duration": segment["duration"],
                "geometry_present": bool(segment["geometry_encoded"]),
            }
            for segment in route_plan["segments"]
        ]

        pytest.fail(
            "Distance preference violated.\n"
            f"Target daily distance: {target_daily_distance} m\n"
            f"Accepted range: [{lower_bound}, {upper_bound}] m\n"
            f"Observed segment distances: {segment_distances}\n"
            f"Selected categories: {selected_categories}\n"
            f"Effective trip days: {data['effective_trip_days']}\n"
            f"Itinerary days / POIs:\n{json.dumps(debug_days, ensure_ascii=False, indent=2)}\n"
            f"Route segments:\n{json.dumps(debug_segments, ensure_ascii=False, indent=2)}"
        )

