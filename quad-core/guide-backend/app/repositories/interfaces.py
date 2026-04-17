"""
Tüm veri erişim katmanları için soyut arayüzler.

Her arayüzün somut implementasyonları kardeş modüllerde bulunur:
  poi_repository.py     → AbstractDataSource, AbstractPoiRepository
  content_repository.py → AbstractContentRepository
  media_repository.py   → AbstractMediaRepository, AbstractAudioAssetResolver

Yeni bir veri kaynağı eklerken (örn. Redis cache, başka bir DB):
  1. İlgili Abstract sınıfı kalıt al.
  2. Tüm @abstractmethod'ları implement et.
  3. containers.py'de yeni sınıfı inject et.
"""
from abc import ABC, abstractmethod

from app.models.enums import Language
from app.models.media import MediaAsset
from app.models.poi import Poi, PoiContent


class AbstractDataSource(ABC):
    """
    POI verisi için altta yatan depolama kaynağını soyutlar.
    (JSON dosya, PostgreSQL, harici API vb.)
    """

    @abstractmethod
    def load_all_pois(self) -> list[Poi]:
        """Kaynaktaki tüm POI'ları yükler ve döner."""
        ...

    @abstractmethod
    def load_by_id(self, poi_id: str) -> Poi | None:
        """Verilen ID'ye sahip POI'yı döner; bulunamazsa None."""
        ...


class AbstractPoiRepository(ABC):
    """POI sorgu operasyonları için veri erişim arayüzü."""

    @abstractmethod
    async def find_by_city(self, city: str) -> list[Poi]:
        """Verilen şehirdeki tüm POI'ları döner."""
        ...

    @abstractmethod
    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        """
        Şehir ve kategori listesine göre POI döner.
        categories boşsa şehirdeki tüm POI'lar döner.
        """
        ...

    @abstractmethod
    async def find_by_id(self, poi_id: str) -> Poi | None:
        """ID'ye göre tek POI döner; bulunamazsa None."""
        ...

    @abstractmethod
    async def find_random(self, limit: int) -> list[Poi]:
        """Veritabanından rastgele en fazla `limit` kadar POI döner."""
        pass


class AbstractContentRepository(ABC):
    """POI metin içeriği ve görsel metadata için veri erişim arayüzü."""

    @abstractmethod
    async def find_content(self, poi_id: str, lang: Language) -> PoiContent | None:
        """
        Belirtilen POI ve dil için içerik döner.
        Dil bulunamazsa EN'e fallback uygulanabilir — implementasyona bağlıdır.
        """
        ...

    @abstractmethod
    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]:
        """
        Birden fazla POI için içerik toplu olarak döner.
        İçerik bulunamayan POI'lar sonuç dict'ine dahil edilmez.
        """
        ...


class AbstractMediaRepository(ABC):
    """Görsel ve ses asset'leri için veri erişim arayüzü."""

    @abstractmethod
    async def get_image(self, poi_id: str) -> MediaAsset | None:
        """POI'nın birincil görsel asset'ini döner; yoksa None."""
        ...

    @abstractmethod
    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """POI için belirtilen dildeki ses asset'ini döner; yoksa None."""
        ...


class AbstractAudioAssetResolver(ABC):
    """Ses asset'i çözümleme mantığı için arayüz."""

    @abstractmethod
    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """POI ve dil için doğru ses asset'ini çözer ve döner."""
        ...
