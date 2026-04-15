"""
Unit tests for OsrmClient.

Covers:
- TC-UT-13: OSRM response parsing extracts distance, duration, and geometry fields.
"""

import pytest

from app.integration.osrm_client import OsrmClient
from app.models.enums import RoutingProfile
from app.models.geo import GeoPoint


class MockResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class MockAsyncClient:
    def __init__(self, payload: dict, *args, **kwargs):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, params=None):
        return MockResponse(self.payload)


@pytest.mark.asyncio
async def test_route_parses_distance_duration_and_geometry(monkeypatch):
    """
    TC-UT-13 — route() must correctly parse distance, duration,
    and geometry from a mocked OSRM route response.
    """
    payload = {
        "routes": [
            {
                "distance": 12345.6,
                "duration": 987.4,
                "geometry": "encoded_polyline_here",
            }
        ]
    }

    monkeypatch.setattr(
        "app.integration.osrm_client.httpx.AsyncClient",
        lambda *args, **kwargs: MockAsyncClient(payload, *args, **kwargs),
    )

    client = OsrmClient(base_url="http://mock-osrm")
    waypoints = [
        GeoPoint(latitude=41.0082, longitude=28.9784),
        GeoPoint(latitude=41.0133, longitude=28.9843),
    ]

    result = await client.route(waypoints, RoutingProfile.DRIVING)

    assert result.distance == 12345
    assert result.duration == 987
    assert result.geometry_encoded == "encoded_polyline_here"


@pytest.mark.asyncio
async def test_trip_parses_distance_duration_and_geometry(monkeypatch):
    """
    TC-UT-13 — trip() must correctly parse distance, duration,
    and geometry from a mocked OSRM trip response.
    """
    payload = {
        "routes": [
            {
                "distance": 54321.9,
                "duration": 1111.8,
                "geometry": "trip_polyline_here",
            }
        ]
    }

    monkeypatch.setattr(
        "app.integration.osrm_client.httpx.AsyncClient",
        lambda *args, **kwargs: MockAsyncClient(payload, *args, **kwargs),
    )

    client = OsrmClient(base_url="http://mock-osrm")
    waypoints = [
        GeoPoint(latitude=41.0082, longitude=28.9784),
        GeoPoint(latitude=41.0133, longitude=28.9843),
    ]

    result = await client.trip(waypoints, RoutingProfile.DRIVING)

    assert result.distance == 54321
    assert result.duration == 1111
    assert result.geometry_encoded == "trip_polyline_here"