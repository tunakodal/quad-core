import os
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.core.containers import create_container
from main import app

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


@pytest.mark.asyncio
async def test_cpu_usage_remains_bounded_under_high_candidate_workload():
    """
    PT-06 — CPU usage remains bounded under high candidate workload.

    Scenario:
    - Upper-bound planning scenario
    - Real system execution (no mocks)

    Expectations:
    - System completes successfully
    - No sustained abnormal CPU spike is observed
    - CPU usage remains proportional to workload
    """

    if psutil is None:
        pytest.skip("psutil is required for PT-06 CPU measurement.")

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

    process = psutil.Process(os.getpid())
    cpu_samples: list[float] = []
    stop_sampling = False

    # Prime psutil CPU measurement
    process.cpu_percent(interval=None)

    def sample_cpu() -> None:
        while not stop_sampling:
            cpu_samples.append(process.cpu_percent(interval=0.2))

    sampler = threading.Thread(target=sample_cpu, daemon=True)
    sampler.start()

    run_count = 3

    try:
        with TestClient(app) as client:
            for _ in range(run_count):
                response = client.post("/api/v1/routes/generate", json=payload)
                assert response.status_code == 200

                data = response.json()
                assert "itinerary" in data
                assert "route_plan" in data
                assert "effective_trip_days" in data
    finally:
        stop_sampling = True
        sampler.join(timeout=2)

    assert len(cpu_samples) > 0

    avg_cpu = sum(cpu_samples) / len(cpu_samples)
    peak_cpu = max(cpu_samples)

    # Practical bounds:
    # - Peak should not become absurdly high for sustained execution
    # - Average should remain in a controlled range
    assert peak_cpu <= 95.0, (
        f"CPU peak appears abnormally high. "
        f"Peak={peak_cpu:.2f}%, Avg={avg_cpu:.2f}%, Samples={cpu_samples}"
    )

    assert avg_cpu <= 80.0, (
        f"CPU average appears too high for bounded workload. "
        f"Peak={peak_cpu:.2f}%, Avg={avg_cpu:.2f}%, Samples={cpu_samples}"
    )