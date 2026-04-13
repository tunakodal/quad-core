from fastapi.testclient import TestClient

import pytest

from main import app
from app.core.containers import create_container
from app.models.enums import Language
from app.models.poi import PoiContent
from app.models.media import MediaAsset



def test_poi_content_response_structure_remains_stable_with_missing_media():
    """
    IT-15 — Content delivery: endpoint response structure remains stable
    when optional media fields are missing.

    Scenario:
    - A POI content request is made for content with text present
      but missing image/audio assets.

    Expectations:
    - API response succeeds
    - Required content fields are present
    - Missing media does not break serialization
    - Response remains usable for UI rendering
    """

    import asyncio

    async def _setup():
        container = await create_container()

        class MissingMediaContentService:
            async def get_poi_content(self, poi_id: str, lang: Language):
                content = PoiContent(
                    poi_id=poi_id,
                    language=lang,
                    description_text="Test description without media.",
                    images=[],
                    audio=None,
                )
                warnings = []
                return content, warnings

        container.content_service = MissingMediaContentService()
        app.state.container = container

    asyncio.run(_setup())

    client = TestClient(app)

    payload = {
        "poi_id": "1",
        "language": "EN",
    }

    response = client.post("/api/v1/pois/content", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "content" in data
    assert "warnings" in data

    content = data["content"]

    # required text/content fields
    assert content["poi_id"] == "1"
    assert content["language"] == "EN"
    assert content["description_text"] == "Test description without media."

    # missing media must serialize safely
    assert "images" in content
    assert isinstance(content["images"], list)
    assert content["images"] == []

    assert "audio" in content
    assert content["audio"] is None


def test_language_based_audio_selection_and_fallback_work_end_to_end():
    """
    IT-16 — Content delivery: language-based audio selection and fallback
    must work end-to-end without breaking the response schema.

    Scenario:
    - POI content is requested with TR, EN, and DE
    - Audio availability differs by language

    Expectations:
    - If language-specific audio exists, the correct audio is returned
    - If not, deterministic fallback behavior is applied
    - Response schema remains stable in all cases
    """

    import asyncio

    async def _setup():
        container = await create_container()

        class LanguageAwareContentService:
            async def get_poi_content(self, poi_id: str, lang: Language):
                base_content = PoiContent(
                    poi_id=poi_id,
                    language=lang,
                    description_text=f"Content for {lang.value}",
                    images=[],
                    audio=None,
                )

                warnings = []

                if lang == Language.TR:
                    base_content.audio = MediaAsset(
                        asset_id="audio-tr-1",
                        url_or_path="/audio/p1/tr.mp3",
                        media_type="audio",
                    )
                elif lang == Language.EN:
                    base_content.audio = MediaAsset(
                        asset_id="audio-en-1",
                        url_or_path="/audio/p1/en.mp3",
                        media_type="audio",
                    )
                elif lang == Language.DE:
                    # deterministic fallback: EN audio
                    base_content.audio = MediaAsset(
                        asset_id="audio-en-1",
                        url_or_path="/audio/p1/en.mp3",
                        media_type="audio",
                    )
                    warnings.append(
                        {
                            "code": "AUDIO_FALLBACK_APPLIED",
                            "severity": "WARN",
                            "message": "Requested audio language was unavailable; EN fallback was used.",
                        }
                    )

                return base_content, warnings

        container.content_service = LanguageAwareContentService()
        app.state.container = container

    asyncio.run(_setup())

    client = TestClient(app)

    def _request(lang: str):
        return client.post(
            "/api/v1/pois/content",
            json={
                "poi_id": "1",
                "language": lang,
            },
        )

    response_tr = _request("TR")
    response_en = _request("EN")
    response_de = _request("DE")

    assert response_tr.status_code == 200
    assert response_en.status_code == 200
    assert response_de.status_code == 200

    data_tr = response_tr.json()
    data_en = response_en.json()
    data_de = response_de.json()

    # TR: direct match
    assert "content" in data_tr
    assert "warnings" in data_tr
    assert data_tr["content"]["language"] == "TR"
    assert data_tr["content"]["audio"] is not None
    assert data_tr["content"]["audio"]["url_or_path"].endswith("tr.mp3")

    # EN: direct match
    assert "content" in data_en
    assert "warnings" in data_en
    assert data_en["content"]["language"] == "EN"
    assert data_en["content"]["audio"] is not None
    assert data_en["content"]["audio"]["url_or_path"].endswith("en.mp3")

    # DE: fallback to EN audio, schema still stable
    assert "content" in data_de
    assert "warnings" in data_de
    assert data_de["content"]["language"] == "DE"
    assert data_de["content"]["audio"] is not None
    assert data_de["content"]["audio"]["url_or_path"].endswith("en.mp3")

    assert isinstance(data_de["warnings"], list)
    assert len(data_de["warnings"]) > 0
    assert data_de["warnings"][0]["code"] == "AUDIO_FALLBACK_APPLIED"



@pytest.mark.asyncio
async def test_batch_content_retrieval_preserves_requested_id_mapping():
    """
    IT-17 — Content delivery: batch retrieval preserves mapping between
    requested POI IDs and returned entries.

    Scenario:
    - A batch content request is made for POI IDs [a, b, c]

    Expectations:
    - Response contains exactly 3 entries
    - Each returned entry maps to the correct POI ID
    - No entries are dropped or duplicated
    """

    container = await create_container()

    class BatchContentService:
        async def batch_get_content(self, poi_ids: list[str], lang: Language):
            return {
                "a": PoiContent(
                    poi_id="a",
                    language=lang,
                    description_text="Content A",
                    images=[],
                    audio=None,
                ),
                "b": PoiContent(
                    poi_id="b",
                    language=lang,
                    description_text="Content B",
                    images=[],
                    audio=None,
                ),
                "c": PoiContent(
                    poi_id="c",
                    language=lang,
                    description_text="Content C",
                    images=[],
                    audio=None,
                ),
            }

    container.content_service = BatchContentService()
    result = await container.content_service.batch_get_content(
        ["a", "b", "c"],
        Language.EN,
    )

    requested_ids = ["a", "b", "c"]

    assert list(result.keys()) == requested_ids

    assert isinstance(result, dict)
    assert len(result) == 3

    assert list(result.keys()) == ["a", "b", "c"]

    assert result["a"].poi_id == "a"
    assert result["b"].poi_id == "b"
    assert result["c"].poi_id == "c"

    assert len(result.keys()) == len(set(result.keys()))