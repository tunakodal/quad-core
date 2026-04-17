"""
Route Endpoints -- API Boundary for route generation, replanning, and trip-day suggestion.

Aligned with GUIDE LLD: RouteController class (Appendix A.1.1).
Dependencies are resolved from the application container at request time.
"""
from fastapi import APIRouter, HTTPException, Request
import httpx
from fastapi.responses import JSONResponse
from starlette.responses import JSONResponse

from app.schemas.common import ApiErrorResponse, ApiWarning, Severity
from app.schemas.route_dtos import ReplanRequest, RouteRequest, RouteResponse
from app.schemas.suggestion_dtos import TripDaySuggestionRequest, TripDaySuggestionResponse
from app.schemas.travel import TravelPreferences
from app.api.validator import RequestValidator
from app.services.itinerary_service import ItineraryService
from app.services.routing_service import RoutingService
from app.services.poi_service import PoiService
from app.core.config import settings
from app.models.route import Itinerary, RoutePlan

router = APIRouter(prefix="/routes", tags=["Routes"])

_ERROR_RESPONSES = {
    400: {"model": ApiErrorResponse},
    404: {"model": ApiErrorResponse},
    422: {"model": ApiErrorResponse},
    500: {"model": ApiErrorResponse},
}


def _calculate_days_from_poi_count(poi_count: int) -> int:
    """
    Returns the recommended maximum number of trip days for a given POI count.

    Thresholds assume approximately 9-14 POIs are visited per day.
    Returns 8 as a fallback for POI counts exceeding 100.
    """
    THRESHOLDS = [
        (9, 1),
        (18, 2),
        (30, 3),
        (45, 4),
        (63, 5),
        (81, 6),
        (100, 7),
    ]

    for limit, days in THRESHOLDS:
        if poi_count <= limit:
            return days
    return 8  # fallback (100+)


class RouteController:
    """
    Handles route generation and replanning endpoints by validating requests,
    orchestrating itinerary and routing services, and returning a normalized
    API response (including warnings) in a stateless workflow.

    Aligned with LLD RouteController interface (Appendix A.1.1).
    """

    def __init__(
        self,
        validator: RequestValidator,
        poi_service: PoiService,
        itinerary_service: ItineraryService,
        routing_service: RoutingService,
    ):
        self._validator = validator
        self._poi_service = poi_service
        self._itinerary_service = itinerary_service
        self._routing_service = routing_service


    async def generate_route(self, req: RouteRequest) -> JSONResponse | RouteResponse:
        """Generate a multi-day itinerary from user preferences."""
        validation = self._validator.validate_route_request(req)
        if not validation.is_valid:
            raise HTTPException(status_code=422, detail=validation.errors)

        pois = await self._poi_service.get_candidate_pois(req.preferences)

        if len(pois) < 2:
            warnings = [
                *validation.warnings,
                ApiWarning(
                    code="INSUFFICIENT_POIS",
                    severity=Severity.WARN,
                    message=(
                        "Not enough POIs match the given filters to build the requested plan. "
                        "Please adjust categories or city, or accept a reduced plan."
                    ),
                ),
            ]

            return RouteResponse(
                itinerary=Itinerary(days=[]),
                route_plan=RoutePlan(
                    segments=[],
                    total_distance=0,
                    total_duration=0,
                    geometry_encoded="",
                ),
                warnings=warnings,
                effective_trip_days=0,
            )

        itinerary, itinerary_warnings = await self._itinerary_service.build_itinerary(
            pois, req.constraints, req.preferences
        )

        try:
            route_plan, routing_warnings = await self._routing_service.generate_route(
                itinerary, req.constraints
            )
        except httpx.HTTPError:
            return JSONResponse(
                status_code=503,
                content={
                    "message": "Route computation failed.",
                    "error_code": "ROUTING_UNAVAILABLE",
                    "details": ["OSRM service is unavailable or unreachable."],
                },
            )

        warnings = [
            *validation.warnings,
            *itinerary_warnings,
            *routing_warnings,
        ]

        used_ids = {
            poi.id
            for day in itinerary.days
            for poi in day.pois
        }
        available_pois = [p for p in pois if p.id not in used_ids]

        return RouteResponse(
            itinerary=itinerary,
            route_plan=route_plan,
            warnings=warnings,
            effective_trip_days=len(itinerary.days),
            available_pois=available_pois,
        )

    async def replan_route(self, req: ReplanRequest) -> JSONResponse | RouteResponse:
        """Replan an existing itinerary after user edits (stateless)."""
        validation = self._validator.validate_replan_request(req)
        if not validation.is_valid:
            raise HTTPException(status_code=422, detail=validation.errors)

        # Derive city from existing itinerary
        city = "unknown"
        if req.existing_itinerary.days:
            first_day = req.existing_itinerary.days[0]
            if first_day.pois:
                city = first_day.pois[0].city

        prefs = TravelPreferences(
            city=city,
            trip_days=req.constraints.max_trip_days,
            categories=[],
            max_distance_per_day = max(req.constraints.max_daily_distance, 1000)
        )

        itinerary, itinerary_warnings = await self._itinerary_service.replan(
            req.existing_itinerary, req.edits, req.constraints, prefs
        )

        try:
            route_plan, routing_warnings = await self._routing_service.update_route_after_edits(
                itinerary, req.edits
            )
        except httpx.HTTPError:
            return JSONResponse(
                status_code=503,
                content={
                    "message": "Route recomputation failed.",
                    "error_code": "ROUTING_UNAVAILABLE",
                    "details": ["OSRM service is unavailable or unreachable."],
                },
            )

        warnings = [
            *validation.warnings,
            *itinerary_warnings,
            *routing_warnings,
        ]

        return RouteResponse(
            itinerary=itinerary,
            route_plan=route_plan,
            warnings=warnings,
        )

    async def suggest_trip_days(
            self, req: TripDaySuggestionRequest
    ) -> TripDaySuggestionResponse:
        """
        Suggests the maximum feasible number of trip days based on the
        number of available POIs for the given city and categories.

        Behavior:
        - Validates the incoming request.
        - Retrieves the number of eligible POIs.
        - Computes a recommended trip duration using a heuristic.
        - Ensures the recommendation does not exceed system limits.
        - Returns non-fatal warnings when the POI pool is likely insufficient.

        The method does not alter core planning logic; warnings are added
        as supplementary information for client guidance.
        """

        # Validate request
        validation = self._validator.validate_trip_day_suggestion_request(req)
        if not validation.is_valid:
            raise HTTPException(status_code=422, detail=validation.errors)

        # Count eligible POIs
        count = await self._poi_service.count_available_pois(
            req.city,
            req.categories,
        )

        # Compute recommended days based on POI count
        max_days = _calculate_days_from_poi_count(count)

        # Clamp to system-wide maximum
        max_days = min(max_days, settings.max_trip_days)

        # Preserve existing validation warnings
        warnings = list(validation.warnings)

        # Add guidance if POI pool is likely insufficient
        # This does not affect the recommendation itself.
        if count < 10:
            warnings.append(
                ApiWarning(
                    code="INSUFFICIENT_POIS",
                    severity=Severity.WARN,
                    message=(
                        "The number of available POIs may be insufficient for the "
                        "requested planning scope. Consider reducing trip duration "
                        "or adjusting selected categories."
                    ),
                )
            )

        return TripDaySuggestionResponse(
            max_recommended_days=max(max_days, 1),  # Ensure at least 1 day
            poi_count=count,
            warnings=warnings,
        )


# -- Lazy controller accessor --

def _get_controller(request: Request) -> RouteController:
    """Resolve RouteController from the application DI container."""
    container = request.app.state.container
    return RouteController(
        validator=container.validator,
        poi_service=container.poi_service,
        itinerary_service=container.itinerary_service,
        routing_service=container.routing_service,
    )


# -- Endpoint wrappers --

@router.post(
    "/generate",
    response_model=RouteResponse,
    responses=_ERROR_RESPONSES,
    summary="Generate a multi-day itinerary and route",
)
async def generate_route(req: RouteRequest, request: Request):
    """Resolves RouteController from the DI container and forwards the route generation request."""
    return await _get_controller(request).generate_route(req)


@router.post(
    "/replan",
    response_model=RouteResponse,
    responses=_ERROR_RESPONSES,
    summary="Replan itinerary after user edits",
)
async def replan_route(req: ReplanRequest, request: Request):
    """Resolves RouteController from the DI container and forwards the replan request."""
    return await _get_controller(request).replan_route(req)


@router.post(
    "/suggest-days",
    response_model=TripDaySuggestionResponse,
    responses=_ERROR_RESPONSES,
    summary="Suggest maximum trip days based on available POIs",
)
async def suggest_trip_days(req: TripDaySuggestionRequest, request: Request):
    """Resolves RouteController from the DI container and forwards the trip-day suggestion request."""
    return await _get_controller(request).suggest_trip_days(req)
