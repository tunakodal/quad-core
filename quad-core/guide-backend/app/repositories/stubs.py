"""
In-memory stub implementations — for unit tests and isolated development.
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
    async def find_by_city(self, city: str) -> list[Poi]:
        return []

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        return []

    async def find_by_id(self, poi_id: str) -> Poi | None:
        return None


class StubContentRepository(AbstractContentRepository):
    async def find_content(self, poi_id: str, lang: Language) -> PoiContent | None:
        return None

    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]:
        return {}


class StubMediaRepository(AbstractMediaRepository):
    async def get_image(self, poi_id: str) -> MediaAsset | None:
        return None

    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        return None


class StubAudioAssetResolver(AbstractAudioAssetResolver):
    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        return None
