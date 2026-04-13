import time
import statistics

import pytest
from fastapi.testclient import TestClient

from app.core.containers import create_container
from main import app


@pytest.mark.asyncio
async def test_large_metadata_retrieval_does_not_introduce_disproportionate_delay():
    """
    PT-03 — Large metadata retrieval does not introduce disproportionate delay.

    Scenario:
    - Large pool city
    - Content metadata retrieval is triggered
    - Real system execution (no mocks)

    Expectations:
    - Content retrieval for a representative day-sized POI set
      does not dominate planning latency
    - Content retrieval remains within a practical end-user waiting bound
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
        # 1) Measure full planning latency
        plan_start = time.perf_counter()
        generate_response = client.post("/api/v1/routes/generate", json=payload)
        plan_elapsed = time.perf_counter() - plan_start

        assert generate_response.status_code == 200
        generated_data = generate_response.json()

        assert "itinerary" in generated_data
        assert "route_plan" in generated_data

        itinerary = generated_data["itinerary"]
        days = itinerary["days"]
        assert len(days) > 0

        # 2) Choose a representative day-sized POI set:
        # average practical day = around 6–7 POIs between 4 and 9.
        representative_day = max(days, key=lambda d: len(d["pois"]))
        representative_poi_ids = [poi["id"] for poi in representative_day["pois"]][:7]

        assert len(representative_poi_ids) > 0

        # 3) Measure content retrieval latency for that representative day
        content_latencies = []
        content_start = time.perf_counter()

        for poi_id in representative_poi_ids:
            single_start = time.perf_counter()
            content_response = client.post(
                "/api/v1/pois/content",
                json={
                    "poi_id": poi_id,
                    "language": "EN",
                },
            )
            single_elapsed = time.perf_counter() - single_start

            assert content_response.status_code == 200
            content_data = content_response.json()

            assert "content" in content_data
            assert "warnings" in content_data
            assert content_data["content"]["poi_id"] == poi_id

            content_latencies.append(single_elapsed)

        total_content_elapsed = time.perf_counter() - content_start
        avg_content_latency = statistics.mean(content_latencies)

    # Content retrieval for a representative day should not dominate planning.
    assert total_content_elapsed <= plan_elapsed * 5.0, (
        f"Representative content retrieval dominates planning latency. "
        f"Planning={plan_elapsed:.3f}s, "
        f"ContentTotal={total_content_elapsed:.3f}s, "
        f"ContentAvg={avg_content_latency:.3f}s, "
        f"RepresentativePOICount={len(representative_poi_ids)}"
    )

    # Practical user-facing waiting bound
    assert total_content_elapsed <= 5.0, (
        f"Representative content retrieval exceeded practical waiting bound. "
        f"ContentTotal={total_content_elapsed:.3f}s, "
        f"ContentAvg={avg_content_latency:.3f}s, "
        f"RepresentativePOICount={len(representative_poi_ids)}"
    )