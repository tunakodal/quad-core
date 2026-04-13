import time
import statistics

import pytest
from fastapi.testclient import TestClient

from app.core.containers import create_container
from main import app


@pytest.mark.asyncio
async def test_typical_usage_latency_satisfies_pr_h01():
    """
    PT-01 — Typical usage latency satisfies PR-H01 (<= 5 seconds).

    Scenario:
    - 1–3 days
    - 3–5 categories
    - Medium/large pool city
    - Real system execution (no mocks)

    Expectations:
    - Average end-to-end latency across multiple runs is <= 5 seconds.
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

    run_count = 5
    latencies = []

    with TestClient(app) as client:
        for _ in range(run_count):
            start = time.perf_counter()
            response = client.post("/api/v1/routes/generate", json=payload)
            elapsed = time.perf_counter() - start

            assert response.status_code == 200
            data = response.json()
            assert "itinerary" in data
            assert "route_plan" in data

            latencies.append(elapsed)

    avg_latency = statistics.mean(latencies)

    assert avg_latency <= 5.0, (
        f"Average latency exceeded PR-H01. "
        f"Average={avg_latency:.3f}s, Runs={[round(x, 3) for x in latencies]}"
    )