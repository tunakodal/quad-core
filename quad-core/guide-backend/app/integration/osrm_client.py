import math
import httpx
from app.models.enums import RoutingProfile
from app.models.geo import GeoPoint
from app.core.config import settings


class OsrmRouteResponse:
    def __init__(
        self,
        distance: int,
        duration: int,
        geometry_encoded: str,
        waypoint_order: list[int],
    ):
        self.distance = distance
        self.duration = duration
        self.geometry_encoded = geometry_encoded
        self.waypoint_order = waypoint_order


class OsrmClient:

    def __init__(
        self,
        base_url: str = settings.osrm_base_url,
        timeout_ms: int = settings.osrm_timeout_ms,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_ms / 1000

    def _coords_str(self, waypoints: list[GeoPoint]) -> str:
        return ";".join(f"{p.longitude},{p.latitude}" for p in waypoints)

    @staticmethod
    def _haversine(a: GeoPoint, b: GeoPoint) -> float:
        R = 6371000
        lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
        dlat = lat2 - lat1
        dlng = math.radians(b.longitude - a.longitude)
        h = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        )
        return 2 * R * math.asin(math.sqrt(h))

    async def trip(
        self,
        waypoints: list[GeoPoint],
        profile: RoutingProfile = RoutingProfile.DRIVING,
    ) -> OsrmRouteResponse:
        """Geliş sırasıyla direkt /route al — sıralama Monte Carlo'da yapıldı."""

        n = len(waypoints)

        if n <= 1:
            return OsrmRouteResponse(
                distance=0,
                duration=0,
                geometry_encoded="",
                waypoint_order=list(range(n)),
            )

        route_coords = self._coords_str(waypoints)
        route_url = f"{self.base_url}/route/v1/{profile.value}/{route_coords}"
        route_params = {
            "overview": "full",
            "geometries": "polyline",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(route_url, params=route_params)
            resp.raise_for_status()
            route_data = resp.json()

        route = route_data["routes"][0]

        return OsrmRouteResponse(
            distance=int(route["distance"]),
            duration=int(route["duration"]),
            geometry_encoded=route["geometry"],
            waypoint_order=list(range(n)),
        )

    async def route(
        self,
        waypoints: list[GeoPoint],
        profile: RoutingProfile = RoutingProfile.DRIVING,
    ) -> OsrmRouteResponse:
        """Verilen sırayla /route — replan için."""
        return await self.trip(waypoints, profile)