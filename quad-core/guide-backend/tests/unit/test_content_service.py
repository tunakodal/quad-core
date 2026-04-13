import pytest

from app.models.enums import Language
from app.models.media import MediaAsset
from app.models.poi import PoiContent
from app.services.content_service import ContentService


class StubContentRepository:
    def __init__(self, content_map):
        self.content_map = content_map

    async def find_content(self, poi_id: str, lang: Language):
        return self.content_map.get((poi_id, lang))

    async def find_content_batch(self, poi_ids: list[str], lang: Language):
        return {
            poi_id: self.content_map[(poi_id, lang)]
            for poi_id in poi_ids
            if (poi_id, lang) in self.content_map
        }


class StubMediaRepository:
    async def get_image(self, poi_id: str):
        return None

    async def get_audio(self, poi_id: str, lang: Language):
        return None


class StubAudioResolver:
    def __init__(self, audio_map):
        self.audio_map = audio_map

    async def resolve_audio(self, poi_id: str, lang: Language):
        return self.audio_map.get((poi_id, lang))


@pytest.fixture
def image_asset():
    return MediaAsset(
        asset_id="img-1",
        url_or_path="/images/p1/01.jpg",
        media_type="image",
    )


@pytest.fixture
def audio_asset_en():
    return MediaAsset(
        asset_id="audio-1-en",
        url_or_path="/audio/p1/en.mp3",
        media_type="audio",
    )


@pytest.fixture
def audio_asset_tr():
    return MediaAsset(
        asset_id="audio-1-tr",
        url_or_path="/audio/p1/tr.mp3",
        media_type="audio",
    )

@pytest.fixture
def audio_asset_de():
    return MediaAsset(
        asset_id="audio-1-de",
        url_or_path="/audio/p1/de.mp3",
        media_type="audio",
    )

@pytest.mark.asyncio
async def test_get_poi_content_returns_text_description(image_asset):
    """
    TC-UT-24 — Content delivery returns text description.
    """
    content_repo = StubContentRepository({
        ("p1", Language.EN): PoiContent(
            poi_id="p1",
            language=Language.EN,
            description_text="A known historical landmark.",
            images=[image_asset],
            audio=None,
        )
    })

    service = ContentService(
        content_repository=content_repo,
        media_repository=StubMediaRepository(),
        audio_asset_resolver=StubAudioResolver({}),
    )

    content, warnings = await service.get_poi_content("p1", Language.EN)

    assert content.description_text is not None
    assert content.description_text.strip() != ""


@pytest.mark.asyncio
async def test_get_poi_content_returns_image_references_when_available(image_asset):
    """
    TC-UT-25 — Content delivery returns image reference(s) when available.
    """
    content_repo = StubContentRepository({
        ("p1", Language.EN): PoiContent(
            poi_id="p1",
            language=Language.EN,
            description_text="Has image.",
            images=[image_asset],
            audio=None,
        )
    })

    service = ContentService(
        content_repository=content_repo,
        media_repository=StubMediaRepository(),
        audio_asset_resolver=StubAudioResolver({}),
    )

    content, warnings = await service.get_poi_content("p1", Language.EN)

    assert content.images is not None
    assert len(content.images) > 0
    assert content.images[0].url_or_path != ""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("lang", "expected_suffix"),
    [
        (Language.EN, "en.mp3"),
        (Language.TR, "tr.mp3"),
        (Language.DE, "de.mp3"),
    ],
)
async def test_get_poi_content_returns_audio_when_available(
    image_asset,
    audio_asset_en,
    audio_asset_tr,
    audio_asset_de,
    lang,
    expected_suffix,
):
    """
    TC-UT-26 — Audio content retrieval succeeds for supported languages when available.
    """
    content_repo = StubContentRepository({
        ("p1", Language.EN): PoiContent(
            poi_id="p1",
            language=Language.EN,
            description_text="English content.",
            images=[image_asset],
            audio=None,
        ),
        ("p1", Language.TR): PoiContent(
            poi_id="p1",
            language=Language.TR,
            description_text="Türkçe içerik.",
            images=[image_asset],
            audio=None,
        ),
        ("p1", Language.DE): PoiContent(
            poi_id="p1",
            language=Language.DE,
            description_text="Deutscher Inhalt.",
            images=[image_asset],
            audio=None,
        ),
    })

    resolver = StubAudioResolver({
        ("p1", Language.EN): audio_asset_en,
        ("p1", Language.TR): audio_asset_tr,
        ("p1", Language.DE): audio_asset_de,
    })

    service = ContentService(
        content_repository=content_repo,
        media_repository=StubMediaRepository(),
        audio_asset_resolver=resolver,
    )

    content, warnings = await service.get_poi_content("p1", lang)

    assert content.audio is not None
    assert content.audio.url_or_path.endswith(expected_suffix)


@pytest.mark.asyncio
async def test_get_poi_content_handles_missing_image_gracefully():
    """
    TC-UT-27 — Missing image is handled gracefully without breaking the response.
    """
    content_repo = StubContentRepository({
        ("p1", Language.EN): PoiContent(
            poi_id="p1",
            language=Language.EN,
            description_text="Text exists even without images.",
            images=[],
            audio=None,
        )
    })

    service = ContentService(
        content_repository=content_repo,
        media_repository=StubMediaRepository(),
        audio_asset_resolver=StubAudioResolver({}),
    )

    content, warnings = await service.get_poi_content("p1", Language.EN)

    assert content.description_text is not None
    assert content.description_text.strip() != ""
    assert content.images == []


@pytest.mark.asyncio
async def test_get_poi_content_handles_missing_audio_gracefully(image_asset):
    """
    TC-UT-28 — Missing audio is handled gracefully without breaking the response.
    """
    content_repo = StubContentRepository({
        ("p1", Language.EN): PoiContent(
            poi_id="p1",
            language=Language.EN,
            description_text="Text exists.",
            images=[image_asset],
            audio=None,
        )
    })

    service = ContentService(
        content_repository=content_repo,
        media_repository=StubMediaRepository(),
        audio_asset_resolver=StubAudioResolver({}),
    )

    content, warnings = await service.get_poi_content("p1", Language.EN)

    assert content.description_text is not None
    assert content.images is not None
    assert content.audio is None
    assert any(w.code == "AUDIO_NOT_FOUND" for w in warnings)


@pytest.mark.asyncio
async def test_batch_get_content_preserves_one_to_one_mapping(image_asset):
    """
    TC-UT-29 — Batch content retrieval preserves one-to-one mapping.
    """
    content_repo = StubContentRepository({
        ("a", Language.EN): PoiContent(
            poi_id="a",
            language=Language.EN,
            description_text="A",
            images=[image_asset],
            audio=None,
        ),
        ("b", Language.EN): PoiContent(
            poi_id="b",
            language=Language.EN,
            description_text="B",
            images=[image_asset],
            audio=None,
        ),
        ("c", Language.EN): PoiContent(
            poi_id="c",
            language=Language.EN,
            description_text="C",
            images=[image_asset],
            audio=None,
        ),
    })

    service = ContentService(
        content_repository=content_repo,
        media_repository=StubMediaRepository(),
        audio_asset_resolver=StubAudioResolver({}),
    )

    result = await service.batch_get_content(["a", "b", "c"], Language.EN)

    assert len(result) == 3
    assert list(result.keys()) == ["a", "b", "c"]
    assert result["a"].poi_id == "a"
    assert result["b"].poi_id == "b"
    assert result["c"].poi_id == "c"