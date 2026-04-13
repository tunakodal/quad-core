import pytest
import httpx

from app.core.containers import create_container
from main import app


@pytest.mark.asyncio
async def test_replanning_updates_propagate_end_to_end_to_routing_and_visualization():
    """
    ST-04 — Scenario 4: replanning updates propagate end-to-end
    to routing and visualization.

    Scenario:
    - An existing Mersin plan is generated
    - Three POIs are removed from one day
    - Two remaining POIs in the same day are reordered
    - The updated plan is submitted for replanning

    Expectations:
    - Updated itinerary is returned successfully
    - Updated route plan is returned successfully
    - Changes are reflected in the final day route output
    - The client can visualize the updated route without errors
    """

    container = await create_container()
    app.state.container = container

    mersin_pois = await container.poi_repository.find_by_city("Mersin")
    assert len(mersin_pois) > 0

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

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        generate_payload = {
            "preferences": {
                "city": "Mersin",
                "trip_days": 1,
                "categories": selected_categories,
                "max_distance_per_day": 100000,
            },
            "constraints": {
                "max_trip_days": 1,
                "max_pois_per_day": 9,
                "max_daily_distance": 100000,
            },
            "language": "EN",
        }

        max_attempts = 50
        generated_data = None
        target_day = None

        for _ in range(max_attempts):
            generate_response = await client.post(
                "/api/v1/routes/generate",
                json=generate_payload,
            )
            assert generate_response.status_code == 200

            candidate_data = generate_response.json()

            assert "itinerary" in candidate_data
            assert "route_plan" in candidate_data

            candidate_days = candidate_data["itinerary"]["days"]
            candidate_target_day = next(
                (day for day in candidate_days if len(day["pois"]) >= 5),
                None,
            )

            if candidate_target_day is not None:
                generated_data = candidate_data
                target_day = candidate_target_day
                break

        if target_day is None:
            pytest.skip(
                "Could not generate a Mersin itinerary with a day containing at least 5 POIs "
                f"after {max_attempts} attempts."
            )

        original_itinerary = generated_data["itinerary"]
        original_days = original_itinerary["days"]
        target_day_index = target_day["day_index"]
        target_day_pois = target_day["pois"]

        original_day_ids = [poi["id"] for poi in target_day_pois]

        removed_ids = original_day_ids[:3]
        remaining_ids = [pid for pid in original_day_ids if pid not in removed_ids]

        assert len(remaining_ids) >= 2

        reordered_ids = [remaining_ids[1], remaining_ids[0], *remaining_ids[2:]]

        replan_payload = {
            "existing_itinerary": original_itinerary,
            "constraints": generate_payload["constraints"],
            "edits": {
                "removed_poi_ids": removed_ids,
                "ordered_poi_ids_by_day": {
                    str(target_day_index): reordered_ids
                },
            },
        }

        replan_response = await client.post(
            "/api/v1/routes/replan",
            json=replan_payload,
        )
        assert replan_response.status_code == 200

        replan_data = replan_response.json()

    assert "itinerary" in replan_data
    assert "route_plan" in replan_data

    updated_itinerary = replan_data["itinerary"]
    updated_route_plan = replan_data["route_plan"]

    assert "days" in updated_itinerary
    assert isinstance(updated_itinerary["days"], list)
    assert len(updated_itinerary["days"]) > 0

    assert "segments" in updated_route_plan
    assert isinstance(updated_route_plan["segments"], list)
    assert len(updated_route_plan["segments"]) > 0

    updated_day = next(day for day in updated_itinerary["days"] if day["day_index"] == target_day_index)
    updated_ids = [poi["id"] for poi in updated_day["pois"]]

    # Removed POIs must no longer appear
    for removed_id in removed_ids:
        assert removed_id not in updated_ids

    # Reordered POIs must appear in the new requested order
    assert updated_ids[:len(reordered_ids)] == reordered_ids

    # No duplicates should be introduced
    assert len(updated_ids) == len(set(updated_ids))

    # Updated route output must remain usable for visualization
    target_segment = next(
        segment for segment in updated_route_plan["segments"]
        if segment["day_index"] == target_day_index
    )

    assert "distance" in target_segment
    assert "duration" in target_segment
    assert "geometry_encoded" in target_segment

    assert target_segment["distance"] >= 0
    assert target_segment["duration"] >= 0
    assert target_segment["geometry_encoded"] != ""

