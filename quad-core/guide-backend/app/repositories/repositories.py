"""
Backward-compatible re-export module.

All repository classes have been moved to focused submodules:
  - app.repositories.interfaces        → Abstract* interfaces
  - app.repositories.poi_repository    → JsonDataSource, PoiRepository
  - app.repositories.content_repository → ContentRepository
  - app.repositories.media_repository  → MediaRepository, AudioAssetResolver
  - app.repositories.stubs             → Stub* test doubles

New code should import directly from those submodules.
This file exists only to avoid breaking existing imports (e.g. tests).
"""
from app.repositories.interfaces import (
    AbstractDataSource,
    AbstractPoiRepository,
    AbstractContentRepository,
    AbstractMediaRepository,
    AbstractAudioAssetResolver,
)
from app.repositories.poi_repository import JsonDataSource, PoiRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.media_repository import MediaRepository, AudioAssetResolver
from app.repositories.stubs import (
    StubPoiRepository,
    StubContentRepository,
    StubMediaRepository,
    StubAudioAssetResolver,
)

__all__ = [
    "AbstractDataSource",
    "AbstractPoiRepository",
    "AbstractContentRepository",
    "AbstractMediaRepository",
    "AbstractAudioAssetResolver",
    "JsonDataSource", "PoiRepository",
    "ContentRepository",
    "MediaRepository", "AudioAssetResolver",
    "StubPoiRepository", "StubContentRepository",
    "StubMediaRepository", "StubAudioAssetResolver",
]
