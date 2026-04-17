"""
Media repository -- image and audio asset resolution.

Two strategies:
  MediaRepository         -- reads from local filesystem (development / fallback)
  PostgresMediaRepository -- reads from Supabase Data API (production)

DB <-> domain model notes:
  media_assets.id     INTEGER -> domain MediaAsset.asset_id: str  (converted with str())
  media_assets.poi_id INTEGER -> queried with int(poi_id)
  url_or_path         Supabase URL or path is passed directly to MediaAsset
"""
from __future__ import annotations

from pathlib import Path

from app.models.enums import Language
from app.models.media import MediaAsset
from app.repositories.interfaces import AbstractAudioAssetResolver, AbstractMediaRepository


# -- Filesystem / development implementation --

class MediaRepository(AbstractMediaRepository):
    """
    Resolves static media assets (images and pre-generated TTS audio)
    from the local filesystem.

    Expected directory structure:
      <media_root>/images/<poi_id>/01.jpg   (or .png / .webp)
      <media_root>/audio/<poi_id>/<lang>.mp3 (or .wav / .ogg)
    """

    def __init__(self, media_root_path: str):
        self._media_root = Path(media_root_path)

    async def get_image(self, poi_id: str) -> MediaAsset | None:
        """
        Returns the first available image for a POI.
        Supported formats: jpg, png, webp (in priority order).
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
        Returns the audio file for a POI in the specified language.
        Supported formats: mp3, wav, ogg (in priority order).
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
    Resolves the correct audio asset for a POI and language.

    Thin wrapper over MediaRepository; makes it easy to wire in alternative
    audio sources (e.g. a TTS API) in the future.
    """

    def __init__(self, media_repository: AbstractMediaRepository):
        self._media_repository = media_repository

    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """Resolves the audio asset for the given POI and language via media repository."""
        return await self._media_repository.get_audio(poi_id, lang)


# -- Supabase Data API implementation --

class PostgresMediaRepository(AbstractMediaRepository):
    """
    Provides media asset access via the Supabase Data API (PostgREST).

    Multiple records may exist in media_assets; rows are ordered by sort_order
    and the first is returned. url_or_path carries the Supabase URL directly.
    """

    def __init__(self, client):
        self._client = client

    async def get_image(self, poi_id: str) -> MediaAsset | None:
        """Fetches the first image asset for a POI from Supabase (sorted by sort_order)."""
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
        """Fetches the first audio asset for a POI and language from Supabase."""
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
