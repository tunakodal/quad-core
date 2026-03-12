from app.models.domain import PoiContent, Language
from app.schemas.dtos import ApiWarning, Severity


class ContentService:
    """
    Aggregates POI descriptions, images, and pre-generated
    multilingual audio references. Supports graceful degradation
    when assets are missing.
    """

    def __init__(self, content_repository, media_repository, audio_asset_resolver):
        self.content_repository = content_repository
        self.media_repository = media_repository
        self.audio_asset_resolver = audio_asset_resolver

    async def get_poi_content(
        self, poi_id: str, lang: Language
    ) -> tuple[PoiContent, list[ApiWarning]]:
        warnings: list[ApiWarning] = []

        content = await self.content_repository.find_content(poi_id, lang)

        if content is None:
            # Graceful degradation: return empty content
            warnings.append(
                ApiWarning(
                    code="CONTENT_NOT_FOUND",
                    severity=Severity.WARN,
                    message=f"No content found for POI {poi_id} in {lang}",
                )
            )
            content = PoiContent(poi_id=poi_id, language=lang)

        # Resolve audio asset
        audio = await self.audio_asset_resolver.resolve_audio(poi_id, lang)
        if audio is None:
            warnings.append(
                ApiWarning(
                    code="AUDIO_NOT_FOUND",
                    severity=Severity.INFO,
                    message=f"No audio guidance for POI {poi_id} in {lang}",
                )
            )
        else:
            content.audio = audio

        return content, warnings

    async def batch_get_content(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]:
        result = {}
        for poi_id in poi_ids:
            content, _ = await self.get_poi_content(poi_id, lang)
            result[poi_id] = content
        return result
