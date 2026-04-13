from app.models.enums import RoutingProfile
from app.models.route import Itinerary, RoutePlan, RouteSegment
from app.schemas.route_dtos import UserEdits
from app.schemas.travel import TravelConstraints
from app.integration.osrm_client import OsrmClient
from app.schemas.common import ApiWarning

class RouteAssembler:
    """Converts OSRM outputs into RoutePlan / RouteSegment structures."""

    def assemble(self, itinerary: Itinerary, osrm_outputs) -> RoutePlan:
        segments: list[RouteSegment] = []
        total_distance = 0
        total_duration = 0
        combined_geometry = ""

        for day, osrm in zip(itinerary.days, osrm_outputs):
            seg = RouteSegment(
                day_index=day.day_index,
                distance=osrm.distance,
                duration=osrm.duration,
                geometry_encoded=osrm.geometry_encoded,
            )
            segments.append(seg)
            total_distance += osrm.distance
            total_duration += osrm.duration
            # Last day geometry used as combined (frontend can decode per-day)
            combined_geometry = osrm.geometry_encoded

        return RoutePlan(
            segments=segments,
            total_distance=total_distance,
            total_duration=total_duration,
            geometry_encoded=combined_geometry,
        )


class RoutingService:
    """
    Coordinates route computation via OSRM and assembles
    results into day-segmented RoutePlan outputs.
    """

    def __init__(self, osrm_client: OsrmClient, route_assembler: RouteAssembler):
        self.osrm_client = osrm_client
        self.route_assembler = route_assembler

    async def generate_route(
            self, itinerary: Itinerary, constraints: TravelConstraints
    ) -> tuple[RoutePlan, list[ApiWarning]]:
        osrm_outputs = []

        for day in itinerary.days:
            if not day.pois:
                continue
            waypoints = [poi.location for poi in day.pois]
            osrm_result = await self.osrm_client.route(
                waypoints, RoutingProfile.DRIVING
            )
            osrm_outputs.append(osrm_result)

        route_plan = self.route_assembler.assemble(itinerary, osrm_outputs)

        for day, seg in zip(itinerary.days, route_plan.segments):
            day.route_segment = seg

        warnings: list[ApiWarning] = []
        return route_plan, warnings

    async def update_route_after_edits(
            self, itinerary: Itinerary, edits: UserEdits
    ) -> tuple[RoutePlan, list[ApiWarning]]:
        """
        Recompute only the days affected by user edits.

        For edited days, the current POI order in the itinerary is treated as
        authoritative and routed with the ordered OSRM route endpoint.
        Unaffected days reuse their existing route segments.
        """
        warnings: list[ApiWarning] = []

        affected_days = {op.day_index for op in edits.reorder_operations}

        affected_days |= {
            day.day_index
            for day in itinerary.days
            for poi in day.pois
            if poi.id in edits.removed_poi_ids
        }

        if edits.ordered_poi_ids_by_day:
            affected_days |= set(edits.ordered_poi_ids_by_day.keys())

        osrm_outputs = []

        for day in itinerary.days:
            if day.day_index in affected_days or not day.route_segment:
                waypoints = [poi.location for poi in day.pois]
                if waypoints:
                    result = await self.osrm_client.route(
                        waypoints,
                        RoutingProfile.DRIVING,
                    )
                    osrm_outputs.append(result)
            else:
                class _Passthrough:
                    def __init__(self, seg):
                        self.distance = seg.distance
                        self.duration = seg.duration
                        self.geometry_encoded = seg.geometry_encoded

                osrm_outputs.append(_Passthrough(day.route_segment))

        route_plan = self.route_assembler.assemble(itinerary, osrm_outputs)

        for day, seg in zip(itinerary.days, route_plan.segments):
            day.route_segment = seg

        return route_plan, warnings