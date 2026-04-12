"""
Media value objects — image and audio asset references.
"""
from pydantic import BaseModel


class MediaAsset(BaseModel):
    """Represents a media resource reference (image or audio)."""
    asset_id: str
    url_or_path: str
    media_type: str  # "image" | "audio"
