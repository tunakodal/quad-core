"""
Dependency Injection Container — Wires all components together.

DATABASE_URL set edilmişse PostgreSQL repo'ları kullanılır.
Set edilmemişse JSON dosya tabanlı repo'lara (geliştirme modu) düşülür.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import asyncpg

from app.core.config import settings
from app.core.database import close_pool, create_pool
from app.integration.osrm_client import OsrmClient
from app.repositories.interfaces import (
    AbstractAudioAssetResolver,
    AbstractContentRepository,
    AbstractMediaRepository,
    AbstractPoiRepository,
)
from app.repositories.poi_repository import (
    JsonDataSource,
    PoiRepository,
    PostgresPoiRepository,
)
from app.repositories.content_repository import (
    ContentRepository,
    PostgresContentRepository,
)
from app.repositories.media_repository import (
    AudioAssetResolver,
    MediaRepository,
    PostgresMediaRepository,
)
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

    # DB pool — varsa uygulama kapanırken kapatılır
    db_pool: Optional[asyncpg.Pool] = field(default=None)


async def create_container() -> AppContainer:
    """
    Tam dependency graph'ı oluşturur.

    DATABASE_URL .env'de tanımlıysa → PostgreSQL
    Tanımlı değilse               → JSON dosyalar (geliştirme modu)
    """
    db_pool: Optional[asyncpg.Pool] = None

    # ── Data Access ───────────────────────────────────────────────
    if settings.database_url:
        db_pool = await create_pool(settings.database_url, use_ssl=settings.db_ssl)
        poi_repository: AbstractPoiRepository = PostgresPoiRepository(db_pool)
        content_repository: AbstractContentRepository = PostgresContentRepository(db_pool)
        media_repository: AbstractMediaRepository = PostgresMediaRepository(db_pool)
    else:
        # Geliştirme modu: JSON dosyalar
        data_source = JsonDataSource(_resolve_data_path("pois.json"))
        poi_repository = PoiRepository(data_source)
        content_repository = ContentRepository(_resolve_data_path("contents.json"))
        media_repository = MediaRepository(settings.media_root_path)

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
    itinerary_service = ItineraryService(planner)

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
        db_pool=db_pool,
    )
