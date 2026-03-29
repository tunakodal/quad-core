"""
Media repository — image and audio asset resolution from the filesystem.

Will be replaced by a database-backed implementation when media assets
are migrated to the media_assets table.
"""
from __future__ import annotations

from pathlib import Path

from app.models.enums import Language
from app.models.media import MediaAsset
from app.repositories.interfaces import AbstractAudioAssetResolver, AbstractMediaRepository


class MediaRepository(AbstractMediaRepository):
    """
    Resolves static media assets (images and pre-generated TTS audio)
    from the local filesystem under media_root_path.
    """

    def __init__(self, media_root_path: str):
        self._media_root = Path(media_root_path)

    async def get_image(self, poi_id: str) -> MediaAsset | None:
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
    """Resolves the correct pre-generated audio asset for a POI and language."""

    def __init__(self, media_repository: AbstractMediaRepository):
        self._media_repository = media_repository

    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        return await self._media_repository.get_audio(poi_id, lang)
