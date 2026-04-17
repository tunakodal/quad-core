"""
POI Endpoints — API Boundary for POI search, detail, and content retrieval.

Aligned with GUIDE LLD: PoiController class (Appendix A.1.1).
Dependencies are resolved from the application container at request time.
"""
from fastapi import APIRouter, HTTPException, Request

from app.models.poi import RandomPoiResponse, RandomPoiItem
from app.schemas.common import ApiErrorResponse
from app.schemas.poi_dtos import PoiContentRequest, PoiContentResponse, PoiQuery, PoiQueryResponse
from app.schemas.travel import TravelPreferences
from app.api.validator import RequestValidator
from app.services.poi_service import PoiService
from app.services.content_service import ContentService
from app.repositories.interfaces import AbstractPoiRepository

router = APIRouter(prefix="/pois", tags=["POIs"])

_ERROR_RESPONSES = {
    400: {"model": ApiErrorResponse},
    404: {"model": ApiErrorResponse},
    422: {"model": ApiErrorResponse},
    500: {"model": ApiErrorResponse},
}


class PoiController:
    """
    Handles POI search, metadata retrieval, and rich content delivery
    (descriptions, media). Aligned with LLD PoiController interface.
    """

    def __init__(
        self,
        validator: RequestValidator,
        poi_service: PoiService,
        content_service: ContentService,
        poi_repository: AbstractPoiRepository,
    ):
        """Controller bagimliliklerini alir ve saklar."""
        self._validator = validator
        self._poi_service = poi_service
        self._content_service = content_service
        self._poi_repository = poi_repository

    async def search_pois(self, query: PoiQuery) -> PoiQueryResponse:
        """Search POIs by city and category filters."""
        validation = self._validator.validate_poi_query(query)
        if not validation.is_valid:
            raise HTTPException(status_code=422, detail=validation.errors)

        prefs = TravelPreferences(
            city=query.city,
            trip_days=1,
            categories=query.categories,
            max_distance_per_day=100_000,
        )
        pois = await self._poi_service.get_candidate_pois(prefs)
        return PoiQueryResponse(pois=pois, warnings=validation.warnings)

    async def get_poi_by_id(self, poi_id: str) -> PoiQueryResponse:
        """Get a single POI by its ID."""
        poi = await self._poi_repository.find_by_id(poi_id)
        if poi is None:
            raise HTTPException(status_code=404, detail=f"POI {poi_id} not found.")
        return PoiQueryResponse(pois=[poi])

    async def get_poi_content(self, req: PoiContentRequest) -> PoiContentResponse:
        """Get description, images, and audio for a POI."""
        content, warnings = await self._content_service.get_poi_content(
            req.poi_id, req.language
        )
        return PoiContentResponse(content=content, warnings=warnings)

    async def get_random_pois(self, limit: int) -> RandomPoiResponse:
        """Kesif ve harita on-yukleme icin rastgele POI listesi doner."""
        pois = await self._poi_service.get_random_pois(limit)

        items = [
            RandomPoiItem(
                id=p.id,
                name=p.name,
                city=p.city,

                main_category_1=p.main_category_1,
                main_category_2=p.main_category_2,
                sub_category_1=p.sub_category_1,
                sub_category_2=p.sub_category_2,
                sub_category_3=p.sub_category_3,
                sub_category_4=p.sub_category_4,

                lat=p.location.latitude,
                lng=p.location.longitude,

                google_rating=p.google_rating,
                google_reviews_total=p.google_reviews_total,
            )
            for p in pois
        ]

        return RandomPoiResponse(items=items)


# ── Lazy controller accessor (resolved from app.state.container) ──

def _get_controller(request: Request) -> PoiController:
    """Resolve PoiController from the application DI container."""
    container = request.app.state.container
    return PoiController(
        validator=container.validator,
        poi_service=container.poi_service,
        content_service=container.content_service,
        poi_repository=container.poi_repository,
    )


# ── Endpoint wrappers ─────────────────────────────────────────────

@router.post(
    "/search",
    response_model=PoiQueryResponse,
    responses=_ERROR_RESPONSES,
    summary="Search POIs by city and category",
)
async def search_pois(query: PoiQuery, request: Request):
    """DI container'dan PoiController'i cozer ve POI arama istegini iletir."""
    return await _get_controller(request).search_pois(query)


@router.post(
    "/content",
    response_model=PoiContentResponse,
    responses=_ERROR_RESPONSES,
    summary="Get POI content (description, images, audio)",
)
async def get_poi_content(req: PoiContentRequest, request: Request):
    """DI container'dan PoiController'i cozer ve icerik istegini iletir."""
    return await _get_controller(request).get_poi_content(req)


@router.get(
    "/random",
    response_model=RandomPoiResponse,
    summary="Get random POIs",
)
async def get_random_pois(request: Request, limit: int = 20):
    """Kesif ve harita on-yukleme icin rastgele POI listesi doner."""
    return await _get_controller(request).get_random_pois(limit)


@router.get(
    "/{poi_id}",
    response_model=PoiQueryResponse,
    responses=_ERROR_RESPONSES,
    summary="Get a single POI by ID",
)
async def get_poi_by_id(poi_id: str, request: Request):
    """DI container'dan PoiController'i cozer ve tekli POI sorgusunu iletir."""
    return await _get_controller(request).get_poi_by_id(poi_id)



