import httpx
from app.models.domain import GeoPoint, RoutingProfile
from app.core.config import settings


class OsrmRouteResponse:
    def __init__(self, distance: int, duration: int, geometry_encoded: str):
        self.distance = distance          # meters
        self.duration = duration          # seconds
        self.geometry_encoded = geometry_encoded


class OsrmClient:
    """
    Communicates with the local OSRM engine via HTTP.
    Constructs route/trip requests and normalizes responses.
    """

    def __init__(
        self,
        base_url: str = settings.osrm_base_url,
        timeout_ms: int = 10_000,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_ms / 1000

    def _coords_str(self, waypoints: list[GeoPoint]) -> str:
        return ";".join(f"{p.longitude},{p.latitude}" for p in waypoints)

    async def route(
        self, waypoints: list[GeoPoint], profile: RoutingProfile = RoutingProfile.DRIVING
    ) -> OsrmRouteResponse:
        """Compute a route through ordered waypoints."""
        coords = self._coords_str(waypoints)
        url = f"{self.base_url}/route/v1/{profile.value}/{coords}"
        params = {
            "overview": "full",
            "geometries": "polyline",
            "steps": "false",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = client.get(url, params=params)  # type: ignore[assignment]
            # httpx sync used here; swap to await client.get() if fully async
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        route = data["routes"][0]
        return OsrmRouteResponse(
            distance=int(route["distance"]),
            duration=int(route["duration"]),
            geometry_encoded=route["geometry"],
        )

    async def trip(
        self, waypoints: list[GeoPoint], profile: RoutingProfile = RoutingProfile.DRIVING
    ) -> OsrmRouteResponse:
        """Compute an optimised round-trip through waypoints."""
        coords = self._coords_str(waypoints)
        url = f"{self.base_url}/trip/v1/{profile.value}/{coords}"
        params = {
            "overview": "full",
            "geometries": "polyline",
            "roundtrip": "true",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        trip = data["trips"][0]
        return OsrmRouteResponse(
            distance=int(trip["distance"]),
            duration=int(trip["duration"]),
            geometry_encoded=trip["geometry"],
        )
