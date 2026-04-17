"""
POI search and content DTOs — request/response shapes for /api/v1/pois/*.
"""
from __future__ import annotations
from typing import Optional

from pydantic import BaseModel

from app.models.enums import Language
from app.models.poi import Poi, PoiContent
from app.schemas.common import ApiWarning


class PoiQuery(BaseModel):
    """Sehir ve kategori bazli POI arama istegi."""
    city: str
    categories: list[str] = []
    text_query: Optional[str] = None


class PoiQueryResponse(BaseModel):
    """POI arama sorgusunun yaniti: eslesen POI listesi ve uyarilar."""
    pois: list[Poi] = []
    warnings: list[ApiWarning] = []


class PoiContentRequest(BaseModel):
    """Bir POI'nin icerigini (aciklama, gorsel, ses) almak icin istek govdesi."""
    poi_id: str
    language: Language = Language.EN


class PoiContentResponse(BaseModel):
    """POI icerik endpoint'inden donen yanit: icerik paketi ve uyarilar."""
    content: PoiContent
    warnings: list[ApiWarning] = []
