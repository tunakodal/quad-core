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

    # Prime psutil measurement
    process.cpu_percent(interval=None)

    def sample_cpu() -> None:
        while not stop_sampling:
            cpu_samples.append(process.cpu_percent(interval=0.2))

    sampler = threading.Thread(target=sample_cpu, daemon=True)
    sampler.start()

    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/routes/generate", json=payload)
            assert response.status_code == 200

            data = response.json()
            assert "itinerary" in data
            assert "route_plan" in data
            assert "effective_trip_days" in data

            time.sleep(1.5)

    finally:
        stop_sampling = True
        sampler.join(timeout=2)

    assert len(cpu_samples) > 0

    avg_cpu = sum(cpu_samples) / len(cpu_samples)
    high_ratio = len([x for x in cpu_samples if x >= 90.0]) / len(cpu_samples)

    tail = cpu_samples[-5:] if len(cpu_samples) >= 5 else cpu_samples
    tail_avg = sum(tail) / len(tail)

    assert avg_cpu <= 90.0, (
        f"Average CPU usage appears too high under bounded workload. "
        f"Avg={avg_cpu:.2f}%, Samples={cpu_samples}"
    )

    assert high_ratio <= 0.60, (
        f"CPU stayed too long at very high utilization. "
        f"HighRatio={high_ratio:.2f}, Avg={avg_cpu:.2f}%, Samples={cpu_samples}"
    )

    assert tail_avg <= 85.0, (
        f"CPU did not begin to normalize after workload completion. "
        f"TailAvg={tail_avg:.2f}%, Avg={avg_cpu:.2f}%, Samples={cpu_samples}"
    )