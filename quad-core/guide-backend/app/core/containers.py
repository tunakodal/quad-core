"""
Dependency Injection Container — Wires all components together.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.core.config import settings
from app.core.database import close_supabase_client, create_supabase_client
from app.integration.osrm_client import OsrmClient
from app.repositories.interfaces import (
    AbstractAudioAssetResolver,
    AbstractContentRepository,
    AbstractMediaRepository,
    AbstractPoiRepository,
)
from app.repositories.poi_repository import PostgresPoiRepository
from app.repositories.content_repository import PostgresContentRepository
from app.repositories.media_repository import AudioAssetResolver, PostgresMediaRepository
from app.services.content_service import ContentService
from app.services.itinerary_builder import ItineraryBuilder
from app.services.itinerary_planner import MonteCarloItineraryPlanner
from app.services.itinerary_service import ItineraryService
from app.services.plan_ranker import HeuristicPlanRanker
from app.services.poi_service import PoiService
from app.services.routing_service import RouteAssembler, RoutingService
from app.api.validator import RequestValidator


def _resolve_data_path(filename: str) -> str:
    """JSON veri dosyalarının yolunu proje köküne göre çözer."""
    current = Path(__file__).resolve()
    project_root = current.parent.parent.parent  # app/core/containers.py → guide-backend/
    return str(project_root / "data" / filename)


@dataclass
class AppContainer:
    """Wired uygulama bileşenlerini tutar."""

    # Data Access
    poi_repository: AbstractPoiRepository
    content_repository: AbstractContentRepository
    media_repository: AbstractMediaRepository
    audio_asset_resolver: AbstractAudioAssetResolver

    # Integration
    osrm_client: OsrmClient

    # Core Services
    poi_service: PoiService
    routing_service: RoutingService
    content_service: ContentService
    itinerary_service: ItineraryService

    # API Boundary
    validator: RequestValidator

    # Supabase client — varsa uygulama kapanırken kapatılır
    supabase_client: Optional[object] = field(default=None)


async def create_container() -> AppContainer:
    """Tam dependency graph'ı oluşturur."""
    # ── Data Access ───────────────────────────────────────────────
    supabase_client = await create_supabase_client(
        settings.supabase_url, settings.supabase_key
    )
    poi_repository: AbstractPoiRepository = PostgresPoiRepository(supabase_client)
    content_repository: AbstractContentRepository = PostgresContentRepository(supabase_client)
    media_repository: AbstractMediaRepository = PostgresMediaRepository(supabase_client)
    audio_asset_resolver: AbstractAudioAssetResolver = AudioAssetResolver(media_repository)

    # ── Integration ───────────────────────────────────────────────
    osrm_client = OsrmClient()

    # ── Core Services ─────────────────────────────────────────────
    poi_service = PoiService(poi_repository)

    route_assembler = RouteAssembler()
    routing_service = RoutingService(osrm_client, route_assembler)

    content_service = ContentService(
        content_repository, media_repository, audio_asset_resolver
    )

    itinerary_builder = ItineraryBuilder()
    plan_ranker = HeuristicPlanRanker()
    planner = MonteCarloItineraryPlanner(itinerary_builder, plan_ranker)
    itinerary_service = ItineraryService(
        planner=planner,
        poi_repository=poi_repository,
    )

    # ── API Boundary ──────────────────────────────────────────────
    validator = RequestValidator()

    return AppContainer(
        poi_repository=poi_repository,
        content_repository=content_repository,
        media_repository=media_repository,
        audio_asset_resolver=audio_asset_resolver,
        osrm_client=osrm_client,
        poi_service=poi_service,
        routing_service=routing_service,
        content_service=content_service,
        itinerary_service=itinerary_service,
        validator=validator,
        supabase_client=supabase_client,
    )
