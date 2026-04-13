import time

import pytest
from fastapi.testclient import TestClient

from app.core.containers import create_container
from main import app


@pytest.mark.asyncio
async def test_on_demand_audio_retrieval_does_not_block_main_interaction_flow():
    """
    PT-07 — On-demand audio retrieval does not block the main interaction flow.

    Scenario:
    - Open POI detail/content
    - Trigger on-demand audio retrieval through POI content loading
    - Immediately continue with a main route interaction (replanning)

    Expectations:
    - POI content loads successfully
    - Audio field is returned on-demand if available, or gracefully absent if unavailable
    - Main interaction flow remains unaffected: replanning still succeeds and
      completes within a practical latency bound
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
        # 1) Generate a normal plan
        generate_response = client.post("/api/v1/routes/generate", json=payload)
        assert generate_response.status_code == 200

        generated_data = generate_response.json()
        assert "itinerary" in generated_data
        assert "route_plan" in generated_data

        itinerary = generated_data["itinerary"]
        assert "days" in itinerary
        assert len(itinerary["days"]) > 0
        assert len(itinerary["days"][0]["pois"]) > 0

        first_poi = itinerary["days"][0]["pois"][0]
        poi_id = first_poi["id"]

        # 2) Trigger POI detail/content loading (audio is part of this payload if available)
        content_start = time.perf_counter()
        content_response = client.post(
            "/api/v1/pois/content",
            json={
                "poi_id": poi_id,
                "language": "EN",
            },
        )
        content_elapsed = time.perf_counter() - content_start

        assert content_response.status_code == 200

        content_data = content_response.json()
        assert "content" in content_data
        assert "warnings" in content_data

        content = content_data["content"]
        assert content["poi_id"] == poi_id
        assert "description_text" in content
        assert "images" in content
        assert "audio" in content

        # audio may be present or absent; both are valid non-blocking outcomes
        # as long as the response remains stable and successful.

        # 3) Immediately continue the main flow with a lightweight replan edit
        target_day = next((d for d in itinerary["days"] if len(d["pois"]) >= 2), None)
        if target_day is None:
            pytest.skip("No suitable day with >=2 POIs for replanning continuity check.")

        target_day_index = target_day["day_index"]
        original_ids = [poi["id"] for poi in target_day["pois"]]
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

        replan_start = time.perf_counter()
        replan_response = client.post("/api/v1/routes/replan", json=replan_payload)
        replan_elapsed = time.perf_counter() - replan_start

    assert replan_response.status_code == 200

    replan_data = replan_response.json()
    assert "itinerary" in replan_data
    assert "route_plan" in replan_data

    updated_itinerary = replan_data["itinerary"]
    updated_route_plan = replan_data["route_plan"]

    assert isinstance(updated_itinerary["days"], list)
    assert len(updated_itinerary["days"]) > 0
    assert isinstance(updated_route_plan["segments"], list)
    assert len(updated_route_plan["segments"]) > 0

    # Practical performance bounds:
    # - content retrieval should be responsive enough for on-demand interaction
    # - subsequent main-flow replanning should remain responsive as well
    assert content_elapsed <= 5.0, (
        f"On-demand content/audio retrieval took too long. "
        f"ContentElapsed={content_elapsed:.3f}s"
    )

    assert replan_elapsed <= 5.0, (
        f"Main interaction flow appears blocked or degraded after content/audio retrieval. "
        f"ReplanElapsed={replan_elapsed:.3f}s, ContentElapsed={content_elapsed:.3f}s"
    )