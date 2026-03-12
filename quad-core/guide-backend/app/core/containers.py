"""
Dependency Injection Container — Wires all components together.

Aligned with GUIDE LLD: each component receives its dependencies
through constructor injection, supporting testability and separation
of concerns.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.integration.osrm_client import OsrmClient
from app.repositories.repositories import (
    JsonDataSource,
    PoiRepository,
    ContentRepository,
    MediaRepository,
    AudioAssetResolver,
    AbstractPoiRepository,
    AbstractContentRepository,
    AbstractMediaRepository,
    AbstractAudioAssetResolver,
)
from app.services.poi_service import PoiService
from app.services.routing_service import RoutingService, RouteAssembler
from app.services.content_service import ContentService
from app.services.itinerary_service import (
    ItineraryService,
    ItineraryBuilder,
    MonteCarloItineraryPlanner,
    HeuristicPlanRanker,
)
from app.api.validator import RequestValidator


def _resolve_data_path(filename: str) -> str:
    """Resolve path to a data file relative to the project root."""
    # Walk up from this file to find the project root (where data/ lives)
    current = Path(__file__).resolve()
    project_root = current.parent.parent.parent  # app/core/containers.py -> guide-backend/
    return str(project_root / "data" / filename)


@dataclass
class AppContainer:
    """Holds all wired application components."""

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


def create_container() -> AppContainer:
    """Factory: build the full dependency graph for production."""

    # ── Data Access ───────────────────────────────────────────────
    data_source = JsonDataSource(_resolve_data_path("pois.json"))
    poi_repository = PoiRepository(data_source)
    content_repository = ContentRepository(_resolve_data_path("contents.json"))
    media_repository = MediaRepository(settings.media_root_path)
    audio_asset_resolver = AudioAssetResolver(media_repository)

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
    )
