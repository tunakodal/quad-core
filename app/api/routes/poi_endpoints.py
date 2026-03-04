from fastapi import APIRouter, HTTPException
from app.schemas.dtos import (
    PoiQuery, PoiQueryResponse,
    PoiContentRequest, PoiContentResponse,
    ApiErrorResponse,
)
from app.api.validator import RequestValidator
from app.services.poi_service import PoiService
from app.services.content_service import ContentService
from app.repositories.repositories import (
    StubPoiRepository, StubContentRepository,
    StubMediaRepository, StubAudioAssetResolver,
)

router = APIRouter(prefix="/pois", tags=["POIs"])

_poi_repo = StubPoiRepository()
_content_repo = StubContentRepository()
_media_repo = StubMediaRepository()
_audio_resolver = StubAudioAssetResolver()
_poi_service = PoiService(_poi_repo)
_content_service = ContentService(_content_repo, _media_repo, _audio_resolver)
_validator = RequestValidator()

_ERROR_RESPONSES = {
    400: {"model": ApiErrorResponse},
    404: {"model": ApiErrorResponse},
    422: {"model": ApiErrorResponse},
    500: {"model": ApiErrorResponse},
}


class PoiController:
    def __init__(
        self,
        validator: RequestValidator,
        poi_service: PoiService,
        content_service: ContentService,
        poi_repository: StubPoiRepository,
    ):
        self._validator = validator
        self._poi_service = poi_service
        self._content_service = content_service
        self._poi_repository = poi_repository

    async def search_pois(self, query: PoiQuery) -> PoiQueryResponse:
        """Search POIs by city and category filters."""
        validation = self._validator.validate_poi_query(query)
        if not validation.is_valid:
            raise HTTPException(status_code=422, detail=validation.errors)

        from app.schemas.dtos import TravelPreferences

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


_controller = PoiController(
    validator=_validator,
    poi_service=_poi_service,
    content_service=_content_service,
    poi_repository=_poi_repo,
)

router.add_api_route(
    "/search",
    _controller.search_pois,
    methods=["POST"],
    response_model=PoiQueryResponse,
    responses=_ERROR_RESPONSES,
)
router.add_api_route(
    "/{poi_id}",
    _controller.get_poi_by_id,
    methods=["GET"],
    response_model=PoiQueryResponse,
    responses=_ERROR_RESPONSES,
)
router.add_api_route(
    "/content",
    _controller.get_poi_content,
    methods=["POST"],
    response_model=PoiContentResponse,
    responses=_ERROR_RESPONSES,
)
