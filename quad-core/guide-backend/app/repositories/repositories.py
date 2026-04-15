"""
Backward-compatible re-export module.

All repository classes have been moved to focused submodules:
  - app.repositories.interfaces         → Abstract* interfaces
  - app.repositories.poi_repository     → PostgresPoiRepository
  - app.repositories.content_repository → PostgresContentRepository
  - app.repositories.media_repository   → AudioAssetResolver, PostgresMediaRepository
  - app.repositories.stubs              → Stub* test doubles

New code should import directly from those submodules.
This file exists only to avoid breaking existing imports (e.g. tests).
"""
from app.repositories.interfaces import (
    AbstractPoiRepository,
    AbstractContentRepository,
    AbstractMediaRepository,
    AbstractAudioAssetResolver,
)
from app.repositories.poi_repository import PostgresPoiRepository
from app.repositories.content_repository import PostgresContentRepository
from app.repositories.media_repository import AudioAssetResolver, PostgresMediaRepository
from app.repositories.stubs import (
    StubPoiRepository,
    StubContentRepository,
    StubMediaRepository,
    StubAudioAssetResolver,
)

__all__ = [
    "AbstractPoiRepository",
    "AbstractContentRepository",
    "AbstractMediaRepository",
    "AbstractAudioAssetResolver",
    "PostgresPoiRepository",
    "PostgresContentRepository",
    "AudioAssetResolver", "PostgresMediaRepository",
    "StubPoiRepository", "StubContentRepository",
    "StubMediaRepository", "StubAudioAssetResolver",
]
