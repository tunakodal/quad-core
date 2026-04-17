"""
Media repository — görsel ve ses asset'i çözümleme.

İki strateji:
  MediaRepository         — yerel dosya sisteminden okur (geliştirme / fallback)
  PostgresMediaRepository — Supabase Data API üzerinden okur (production)

DB ↔ domain model farkları:
  media_assets.id     INTEGER → domain MediaAsset.asset_id: str  (str() ile dönüştürülür)
  media_assets.poi_id INTEGER → sorguda int(poi_id) ile kullanılır
  url_or_path         Supabase'den gelen URL veya yol doğrudan MediaAsset'e aktarılır
"""
from __future__ import annotations

from pathlib import Path

from app.models.enums import Language
from app.models.media import MediaAsset
from app.repositories.interfaces import AbstractAudioAssetResolver, AbstractMediaRepository


# ── Dosya sistemi / geliştirme implementasyonu ────────────────────

class MediaRepository(AbstractMediaRepository):
    """
    Statik medya asset'lerini (görseller ve önceden üretilmiş TTS sesleri)
    yerel dosya sisteminden çözer.

    Beklenen dizin yapısı:
      <media_root>/images/<poi_id>/01.jpg   (veya .png / .webp)
      <media_root>/audio/<poi_id>/<lang>.mp3 (veya .wav / .ogg)
    """

    def __init__(self, media_root_path: str):
        """Nesneyi baslatir."""
        self._media_root = Path(media_root_path)

    async def get_image(self, poi_id: str) -> MediaAsset | None:
        """
        POI'nın ilk görselini döner.
        Desteklenen formatlar: jpg, png, webp (öncelik sırası).
        """
        img_dir = self._media_root / "images" / poi_id
        if img_dir.exists():
            for ext in ("jpg", "png", "webp"):
                candidate = img_dir / f"01.{ext}"
                if candidate.exists():
                    return MediaAsset(
                        asset_id=f"{poi_id}-img-01",
                        url_or_path=str(candidate),
                        media_type="image",
                    )
        return None

    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """
        POI için belirtilen dildeki ses dosyasını döner.
        Desteklenen formatlar: mp3, wav, ogg (öncelik sırası).
        """
        audio_dir = self._media_root / "audio" / poi_id
        lang_lower = lang.value.lower()
        for ext in ("mp3", "wav", "ogg"):
            candidate = audio_dir / f"{lang_lower}.{ext}"
            if candidate.exists():
                return MediaAsset(
                    asset_id=f"{poi_id}-audio-{lang_lower}",
                    url_or_path=str(candidate),
                    media_type="audio",
                )
        return None


class AudioAssetResolver(AbstractAudioAssetResolver):
    """
    POI ve dil için doğru ses asset'ini çözer.

    MediaRepository üzerinde oturan ince bir sarmalayıcıdır;
    gelecekte farklı ses kaynaklarını (örn. TTS API) buraya bağlamak kolaylaşır.
    """

    def __init__(self, media_repository: AbstractMediaRepository):
        """Nesneyi baslatir."""
        self._media_repository = media_repository

    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """Verilen POI ve dil icin ses asset'ini media repository uzerinden cozer."""
        return await self._media_repository.get_audio(poi_id, lang)


# ── Supabase Data API implementasyonu ────────────────────────────

class PostgresMediaRepository(AbstractMediaRepository):
    """
    Supabase Data API (PostgREST) üzerinden medya asset erişimi sağlar.

    media_assets tablosunda birden fazla kayıt olabilir; sort_order'a göre
    sıralanır ve ilk kayıt döndürülür. url_or_path alanı Supabase'den
    gelen URL veya dosya yolunu doğrudan taşır.
    """

    def __init__(self, client):
        """Nesneyi baslatir."""
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
