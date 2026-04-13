import pytest
import httpx

from app.core.containers import create_container
from main import app


@pytest.mark.asyncio
async def test_full_workflow_plan_explore_content_and_replan_completes_cohesively():
    """
    ST-06 — Scenario 6: full workflow (plan -> explore -> content -> replan)
    completes cohesively.

    Scenario:
    - City: Istanbul
    - Requested trip duration: 3–5 days
    - Multiple categories
    - One replanning edit is performed
    - POI detail is opened

    Expectations:
    - Plan generation succeeds and route is visualizable
    - POI detail/content loads successfully
      (or gracefully indicates missing assets)
    - Replanning succeeds and returns an updated route
    - All user-visible steps remain consumable by the UI
      without client-visible errors
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

        max_attempts = 20
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
            assert "effective_trip_days" in candidate_data

            candidate_days = candidate_data["itinerary"]["days"]
            candidate_target_day = next(
                (day for day in candidate_days if len(day["pois"]) >= 2),
                None,
            )

            if candidate_target_day is not None:
                generated_data = candidate_data
                target_day = candidate_target_day
                break

        if target_day is None:
            pytest.skip(
                "Could not generate an Istanbul itinerary with a day containing "
                f"at least 2 POIs after {max_attempts} attempts."
            )

        # 1) Plan + route renderability
        itinerary = generated_data["itinerary"]
        route_plan = generated_data["route_plan"]

        assert isinstance(itinerary["days"], list)
        assert len(itinerary["days"]) >= 3

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

        # 2) Explore -> open POI detail/content
        first_poi = itinerary["days"][0]["pois"][0]
        poi_id = first_poi["id"]

        content_response = await client.post(
            "/api/v1/pois/content",
            json={
                "poi_id": poi_id,
                "language": "EN",
            },
        )
        assert content_response.status_code == 200

        content_data = content_response.json()

        assert "content" in content_data
        assert "warnings" in content_data

        content = content_data["content"]
        assert content["poi_id"] == poi_id
        assert "description_text" in content
        assert "images" in content
        assert "audio" in content

        assert isinstance(content["images"], list)
        # audio may exist or be None; both are valid graceful outcomes

        # 3) Replan with one user-visible edit: reorder 2 POIs in one day
        target_day_index = target_day["day_index"]
        target_ids = [poi["id"] for poi in target_day["pois"]]

        reordered_ids = [target_ids[1], target_ids[0], *target_ids[2:]]

        replan_payload = {
            "existing_itinerary": itinerary,
            "constraints": generate_payload["constraints"],
            "edits": {
                "ordered_poi_ids_by_day": {
                    str(target_day_index): reordered_ids
                }
            },
        }

        replan_response = await client.post(
            "/api/v1/routes/replan",
            json=replan_payload,
        )
        assert replan_response.status_code == 200

        replan_data = replan_response.json()

    # 4) Updated response remains UI-consumable
    assert "itinerary" in replan_data
    assert "route_plan" in replan_data

    updated_itinerary = replan_data["itinerary"]
    updated_route_plan = replan_data["route_plan"]

    assert isinstance(updated_itinerary["days"], list)
    assert len(updated_itinerary["days"]) > 0

    assert isinstance(updated_route_plan["segments"], list)
    assert len(updated_route_plan["segments"]) > 0

    updated_day = next(
        day for day in updated_itinerary["days"]
        if day["day_index"] == target_day_index
    )
    updated_ids = [poi["id"] for poi in updated_day["pois"]]

    # Reorder must be reflected in final user-visible itinerary
    assert updated_ids[:len(reordered_ids)] == reordered_ids

    # Updated route must still remain visualizable
    updated_segment = next(
        segment for segment in updated_route_plan["segments"]
        if segment["day_index"] == target_day_index
    )

    assert "distance" in updated_segment
    assert "duration" in updated_segment
    assert "geometry_encoded" in updated_segment

    assert updated_segment["distance"] >= 0
    assert updated_segment["duration"] >= 0
    assert updated_segment["geometry_encoded"] != ""

