import pytest
import httpx

from app.core.containers import create_container
from main import app


@pytest.mark.asyncio
async def test_adding_pois_via_replanning_works_end_to_end_without_breaking_other_days():
    """
    ST-05 — Scenario 5: adding POIs via replanning works end-to-end
    without breaking other days.

    Scenario:
    - An existing Istanbul plan is generated
    - One or more POIs are added to a chosen day/position
    - Replan is submitted

    Expectations:
    - Replanned response is returned successfully
    - Response remains consumable by the UI
    - Added POIs appear in the updated day route visualization
    - Unrelated days remain stable from the user's perspective
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

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        generate_payload = {
            "preferences": {
                "city": "Istanbul",
                "trip_days": 2,
                "categories": selected_categories,
                "max_distance_per_day": 100000,
            },
            "constraints": {
                "max_trip_days": 2,
                "max_pois_per_day": 9,
                "max_daily_distance": 100000,
            },
            "language": "EN",
        }

        generate_response = await client.post(
            "/api/v1/routes/generate",
            json=generate_payload,
        )
        assert generate_response.status_code == 200

        generated_data = generate_response.json()
        original_itinerary = generated_data["itinerary"]
        original_route_plan = generated_data["route_plan"]

        assert "days" in original_itinerary
        assert len(original_itinerary["days"]) >= 2

        target_day = original_itinerary["days"][0]
        other_day = original_itinerary["days"][1]

        target_day_index = target_day["day_index"]
        other_day_index = other_day["day_index"]

        target_original_ids = [poi["id"] for poi in target_day["pois"]]
        other_day_original_ids = [poi["id"] for poi in other_day["pois"]]

        # Get candidate POIs from the API and choose one that is not already in the itinerary
        search_payload = {
            "city": "Istanbul",
            "categories": selected_categories,
        }

        search_response = await client.post(
            "/api/v1/pois/search",
            json=search_payload,
        )
        assert search_response.status_code == 200

        search_data = search_response.json()
        all_candidate_ids = [poi["id"] for poi in search_data["pois"]]

        all_existing_ids = {
            poi["id"]
            for day in original_itinerary["days"]
            for poi in day["pois"]
        }

        add_ids = [pid for pid in all_candidate_ids if pid not in all_existing_ids]
        assert len(add_ids) >= 1

        # Add one new POI at the beginning of the chosen day
        added_id = add_ids[0]
        updated_target_order = [added_id, *target_original_ids]

        replan_payload = {
            "existing_itinerary": original_itinerary,
            "constraints": generate_payload["constraints"],
            "edits": {
                "ordered_poi_ids_by_day": {
                    str(target_day_index): updated_target_order
                }
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
    assert len(updated_itinerary["days"]) >= 2

    assert "segments" in updated_route_plan
    assert isinstance(updated_route_plan["segments"], list)
    assert len(updated_route_plan["segments"]) >= 2

    updated_target_day = next(
        day for day in updated_itinerary["days"]
        if day["day_index"] == target_day_index
    )
    updated_other_day = next(
        day for day in updated_itinerary["days"]
        if day["day_index"] == other_day_index
    )

    updated_target_ids = [poi["id"] for poi in updated_target_day["pois"]]
    updated_other_day_ids = [poi["id"] for poi in updated_other_day["pois"]]

    # Added POI must appear in the updated target day
    assert added_id in updated_target_ids
    assert updated_target_ids[0] == added_id

    # Existing target day POIs must still remain unless intentionally changed
    for pid in target_original_ids:
        assert pid in updated_target_ids

    # No duplicates in the updated target day
    assert len(updated_target_ids) == len(set(updated_target_ids))

    # Unrelated day must remain unchanged from the user's perspective
    assert updated_other_day_ids == other_day_original_ids

    # Updated target day route must remain visualizable
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

    # Unrelated day route should still remain present and consumable
    other_segment = next(
        segment for segment in updated_route_plan["segments"]
        if segment["day_index"] == other_day_index
    )

    assert "distance" in other_segment
    assert "duration" in other_segment
    assert "geometry_encoded" in other_segment
    assert other_segment["geometry_encoded"] != ""

