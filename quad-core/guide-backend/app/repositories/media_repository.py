"""
Media repository — Supabase Data API üzerinden görsel ve ses asset erişimi.

DB ↔ domain model farkları:
  media_assets.id     INTEGER → domain MediaAsset.asset_id: str  (str() ile dönüştürülür)
  media_assets.poi_id INTEGER → sorguda int(poi_id) ile kullanılır
  url_or_path         Supabase'den gelen URL veya yol doğrudan MediaAsset'e aktarılır
"""
from __future__ import annotations

from app.models.enums import Language
from app.models.media import MediaAsset
from app.repositories.interfaces import AbstractAudioAssetResolver, AbstractMediaRepository


class AudioAssetResolver(AbstractAudioAssetResolver):
    """
    POI ve dil için doğru ses asset'ini çözer.

    MediaRepository üzerinde oturan ince bir sarmalayıcıdır;
    gelecekte farklı ses kaynaklarını (örn. TTS API) buraya bağlamak kolaylaşır.
    """

    def __init__(self, media_repository: AbstractMediaRepository):
        self._media_repository = media_repository

    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        return await self._media_repository.get_audio(poi_id, lang)


class PostgresMediaRepository(AbstractMediaRepository):
    """
    Supabase Data API (PostgREST) üzerinden medya asset erişimi sağlar.

    media_assets tablosunda birden fazla kayıt olabilir; sort_order'a göre
    sıralanır ve ilk kayıt döndürülür. url_or_path alanı Supabase'den
    gelen URL veya dosya yolunu doğrudan taşır.
    """

    def __init__(self, client):
        self._client = client

    async def get_image(self, poi_id: str) -> MediaAsset | None:
        """POI'nın ilk görsel asset'ini Supabase'den çeker (sort_order'a göre sıralı)."""
        response = await (
            self._client.table("media_assets")
            .select("id, url_or_path, media_type")
            .eq("poi_id", int(poi_id))
            .eq("media_type", "image")
            .order("sort_order")
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        row = response.data[0]
        return MediaAsset(
            asset_id=str(row["id"]),
            url_or_path=row["url_or_path"],
            media_type="image",
        )

    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """POI için belirtilen dildeki ilk ses asset'ini Supabase'den çeker."""
        response = await (
            self._client.table("media_assets")
            .select("id, url_or_path, media_type")
            .eq("poi_id", int(poi_id))
            .eq("media_type", "audio")
            .eq("language", lang.value)
            .order("sort_order")
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        row = response.data[0]
        return MediaAsset(
            asset_id=str(row["id"]),
            url_or_path=row["url_or_path"],
            media_type="audio",
        )
