from app.models.enums import Language
from app.models.poi import PoiContent
from app.schemas.common import ApiWarning, Severity


class ContentService:
    """
    Aggregates POI descriptions, images, and pre-generated
    multilingual audio references. Supports graceful degradation
    when assets are missing.
    """

    def __init__(self, content_repository, media_repository, audio_asset_resolver):
        """
        Args:
            content_repository:    Metin içeriği ve görsel metadata için veri kaynağı.
            media_repository:      Görsel ve ses asset'leri için veri kaynağı.
            audio_asset_resolver:  Doğru ses dosyasını seçen çözümleyici.
        """
        self.content_repository = content_repository
        self.media_repository = media_repository
        self.audio_asset_resolver = audio_asset_resolver

    async def get_poi_content(
        self, poi_id: str, lang: Language
    ) -> tuple[PoiContent, list[ApiWarning]]:
        """
        Bir POI için metin içeriği ve ses asset'ini bir arada döner.

        İçerik bulunamazsa CONTENT_NOT_FOUND uyarısıyla boş PoiContent döner
        (graceful degradation — 404 fırlatmaz). Ses bulunamazsa AUDIO_NOT_FOUND
        INFO uyarısı eklenir ancak içerik yine de döner.

        Args:
            poi_id: İçeriği istenen mekanın kimliği.
            lang:   İstenen içerik dili.

        Returns:
            (PoiContent, warnings) tuple'ı.
        """
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
        """
        Birden fazla POI için içerikleri toplu olarak çeker.

        get_poi_content'i sırayla çağırır; içerik bulunamayan POI'lar için
        boş PoiContent oluşturulur (uyarılar bu metodda yoksayılır).

        Args:
            poi_ids: İçerik istenen mekan kimliklerinin listesi.
            lang:    İstenen içerik dili.

        Returns:
            {poi_id: PoiContent} eşlemesi. Tüm poi_id'ler sonuçta bulunur.
        """
        result = {}
        for poi_id in poi_ids:
            content, _ = await self.get_poi_content(poi_id, lang)
            result[poi_id] = content
        return result
