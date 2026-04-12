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
    city: str
    categories: list[str] = []
    text_query: Optional[str] = None


class PoiQueryResponse(BaseModel):
    pois: list[Poi] = []
    warnings: list[ApiWarning] = []


class PoiContentRequest(BaseModel):
    poi_id: str
    language: Language = Language.EN


class PoiContentResponse(BaseModel):
    content: PoiContent
    warnings: list[ApiWarning] = []
