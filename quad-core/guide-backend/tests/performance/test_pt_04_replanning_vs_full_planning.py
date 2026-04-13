import time

import pytest
from fastapi.testclient import TestClient

from app.core.containers import create_container
from main import app


@pytest.mark.asyncio
async def test_replanning_latency_remains_comparable_to_full_planning():
    """
    PT-04 — Replanning latency remains comparable to full planning.

    Scenario:
    - Typical itinerary is generated
    - Limited edits (reorder) are applied
    - Replanning is triggered

    Expectations:
    - Replanning completes successfully
    - Replanning latency remains comparable to full planning latency
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
            if len(discovered_categories) == 5:
                break
        if len(discovered_categories) == 5:
            break

    selected_categories = discovered_categories[:3]
    assert len(selected_categories) >= 3

    payload = {
        "preferences": {
            "city": "Istanbul",
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
        # 1) Full planning latency
        plan_start = time.perf_counter()
        generate_response = client.post("/api/v1/routes/generate", json=payload)
        plan_elapsed = time.perf_counter() - plan_start

        assert generate_response.status_code == 200
        generated_data = generate_response.json()

        itinerary = generated_data["itinerary"]
        route_plan = generated_data["route_plan"]

        assert "days" in itinerary
        assert len(itinerary["days"]) > 0

        # 2) Choose a day with at least 2 POIs for reorder
        target_day = next(
            (d for d in itinerary["days"] if len(d["pois"]) >= 2),
            None
        )

        if target_day is None:
            pytest.skip("No suitable day with >=2 POIs for replanning test")

        target_day_index = target_day["day_index"]
        original_ids = [poi["id"] for poi in target_day["pois"]]

        # simple reorder (swap first two)
        reordered_ids = [original_ids[1], original_ids[0], *original_ids[2:]]

        replan_payload = {
            "existing_itinerary": itinerary,
            "constraints": payload["constraints"],
            "edits": {
                "ordered_poi_ids_by_day": {
                    str(target_day_index): reordered_ids
                }
            },
        }

        # 3) Replanning latency
        replan_start = time.perf_counter()
        replan_response = client.post("/api/v1/routes/replan", json=replan_payload)
        replan_elapsed = time.perf_counter() - replan_start

    assert replan_response.status_code == 200

    replan_data = replan_response.json()

    assert "itinerary" in replan_data
    assert "route_plan" in replan_data

    # Core assertion: comparable latency
    assert replan_elapsed <= plan_elapsed * 1.3, (
        f"Replanning latency not comparable to planning. "
        f"Planning={plan_elapsed:.3f}s, "
        f"Replanning={replan_elapsed:.3f}s"
    )

    # Optional absolute sanity bound (nice to have)
    assert replan_elapsed <= 5.0, (
        f"Replanning latency exceeds acceptable bound. "
        f"Replanning={replan_elapsed:.3f}s"
    )