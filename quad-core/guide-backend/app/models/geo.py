"""
Geographic value objects (WGS84 coordinates).
"""
from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    """Represents a geographical coordinate (WGS84)."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
