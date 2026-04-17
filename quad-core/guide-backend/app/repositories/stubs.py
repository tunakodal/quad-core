"""
In-memory stub implementations -- for unit tests and isolated development.
"""
from __future__ import annotations

from app.models.enums import Language
from app.models.media import MediaAsset
from app.models.poi import Poi, PoiContent
from app.repositories.interfaces import (
    AbstractAudioAssetResolver,
    AbstractContentRepository,
    AbstractMediaRepository,
    AbstractPoiRepository,
)


class StubPoiRepository(AbstractPoiRepository):
    """POI repository test double that always returns empty results."""

    async def find_by_city(self, city: str) -> list[Poi]:
        """Test double -- always returns empty list."""
        return []

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        """Test double -- always returns empty list."""
        return []

    async def find_by_id(self, poi_id: str) -> Poi | None:
        """Test double -- always returns None."""
        return None

    async def find_random(self, limit: int) -> list[Poi]:
        """Test double -- always returns empty list."""
        return []


class StubContentRepository(AbstractContentRepository):
    """Content repository test double that always returns empty results."""

    async def find_content(self, poi_id: str, lang: Language) -> PoiContent | None:
        """Test double -- always returns None."""
        return None

    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]:
        """Test double -- always returns empty dict."""
        return {}


class StubMediaRepository(AbstractMediaRepository):
    """Media repository test double that always returns empty results."""

    async def get_image(self, poi_id: str) -> MediaAsset | None:
        """Test double -- always returns None."""
        return None

    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """Test double -- always returns None."""
        return None


class StubAudioAssetResolver(AbstractAudioAssetResolver):
    """Audio asset resolver test double that always returns None."""

    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """Test double -- always returns None."""
        return None
