import pytest
from fastapi.testclient import TestClient

from app.core.containers import create_container
from main import app



@pytest.mark.asyncio
async def test_end_to_end_flow_returns_user_facing_insufficiency_guidance():
    """
    ST-02 — Scenario 2: end-to-end flow returns user-facing insufficiency
    guidance without breaking the workflow.

    Scenario:
    - City: Yalova
    - Requested trip duration: 2 days
    - Limited category selection
    - No explicit distance preference beyond the required request field

    Expectations:
    - System returns a successful response for the planning workflow
    - A user-facing insufficiency warning is included
    - The warning guides the user to adjust categories or accept a reduced plan
    - Response schema remains usable for UI consumption
    """

    container = await create_container()
    app.state.container = container

    payload = {
        "preferences": {
            "city": "Yalova",
            "trip_days": 2,
            "categories": ["Museum"],
            "max_distance_per_day": 100000,
        },
        "constraints": {
            "max_trip_days": 2,
            "max_pois_per_day": 9,
            "max_daily_distance": 100000,
        },
        "language": "EN",
    }

    with TestClient(app) as client:
        response = client.post("/api/v1/routes/generate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "itinerary" in data
    assert "route_plan" in data
    assert "warnings" in data

    assert isinstance(data["warnings"], list)
    assert len(data["warnings"]) > 0

    warning_codes = [warning.get("code") for warning in data["warnings"]]
    warning_messages = [
        str(warning.get("message", "")).lower()
        for warning in data["warnings"]
    ]

    assert "PARTIAL_ITINERARY" in warning_codes or "INSUFFICIENT_POIS" in warning_codes

    assert any(
        "insufficient" in message
        or "adjust" in message
        or "reduce" in message
        or "could not be fully satisfied" in message
        for message in warning_messages
    )

    # Response must remain consumable by the UI
    assert isinstance(data["itinerary"], dict)
    assert isinstance(data["route_plan"], dict)

