import gc
import os
import time

import pytest
from fastapi.testclient import TestClient

from app.core.containers import create_container
from main import app

try:
    import psutil
except ImportError:
    psutil = None


@pytest.mark.asyncio
async def test_backend_memory_usage_remains_stable_across_repeated_executions():
    """
    PT-05 — Backend memory usage remains stable across repeated executions.

    Scenario:
    - Repeated planning + replanning cycles
    - Real system execution (no mocks)

    Expectations:
    - No progressive memory growth indicative of a leak
    - Memory usage plateaus within a reasonable tolerance
    """

    if psutil is None:
        pytest.skip("psutil is required for PT-05 memory measurement.")

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

    process = psutil.Process(os.getpid())
    memory_samples_mb: list[float] = []

    cycle_count = 20

    with TestClient(app) as client:
        for _ in range(cycle_count):
            # planning
            generate_response = client.post("/api/v1/routes/generate", json=payload)
            assert generate_response.status_code == 200

            generated_data = generate_response.json()
            itinerary = generated_data["itinerary"]
            days = itinerary["days"]
            assert len(days) > 0

            target_day = next((d for d in days if len(d["pois"]) >= 2), None)
            if target_day is None:
                pytest.skip("No suitable day with >=2 POIs for replanning cycle.")

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

            # replanning
            replan_response = client.post("/api/v1/routes/replan", json=replan_payload)
            assert replan_response.status_code == 200

            # encourage cleanup between iterations
            del generate_response, generated_data, itinerary, days
            del replan_payload, replan_response
            gc.collect()
            time.sleep(0.1)

            rss_mb = process.memory_info().rss / (1024 * 1024)
            memory_samples_mb.append(rss_mb)

    assert len(memory_samples_mb) == cycle_count

    start_mb = memory_samples_mb[0]
    end_mb = memory_samples_mb[-1]
    peak_mb = max(memory_samples_mb)
    growth_mb = end_mb - start_mb

    # Accept modest fluctuation, reject clear progressive leak pattern.
    assert growth_mb <= 50.0, (
        f"Memory growth appears too high across repeated cycles. "
        f"Start={start_mb:.2f} MB, End={end_mb:.2f} MB, "
        f"Growth={growth_mb:.2f} MB, Peak={peak_mb:.2f} MB, "
        f"Samples={[round(x, 2) for x in memory_samples_mb]}"
    )

    # Peak should not explode relative to starting footprint.
    assert peak_mb <= start_mb + 80.0, (
        f"Peak memory appears unstable. "
        f"Start={start_mb:.2f} MB, Peak={peak_mb:.2f} MB, "
        f"Samples={[round(x, 2) for x in memory_samples_mb]}"
    )