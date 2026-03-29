"""
Abstract repository interfaces for all data access layers.

Implementations live in the sibling modules:
  poi_repository.py     → AbstractDataSource, AbstractPoiRepository
  content_repository.py → AbstractContentRepository
  media_repository.py   → AbstractMediaRepository, AbstractAudioAssetResolver
"""
from abc import ABC, abstractmethod

from app.models.enums import Language
from app.models.media import MediaAsset
from app.models.poi import Poi, PoiContent


class AbstractDataSource(ABC):
    """Abstracts the underlying POI storage (JSON file, PostgreSQL, etc.)."""

    @abstractmethod
    def load_all_pois(self) -> list[Poi]: ...

    @abstractmethod
    def load_by_id(self, poi_id: str) -> Poi | None: ...


class AbstractPoiRepository(ABC):
    @abstractmethod
    async def find_by_city(self, city: str) -> list[Poi]: ...

    @abstractmethod
    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]: ...

    @abstractmethod
    async def find_by_id(self, poi_id: str) -> Poi | None: ...


class AbstractContentRepository(ABC):
    @abstractmethod
    async def find_content(self, poi_id: str, lang: Language) -> PoiContent | None: ...

    @abstractmethod
    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]: ...


class AbstractMediaRepository(ABC):
    @abstractmethod
    async def get_image(self, poi_id: str) -> MediaAsset | None: ...

    @abstractmethod
    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None: ...


class AbstractAudioAssetResolver(ABC):
    @abstractmethod
    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None: ...
