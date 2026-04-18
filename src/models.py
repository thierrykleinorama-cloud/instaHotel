"""
Pydantic models for Claude Vision analysis and media items.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# Valid values for structured fields
VALID_CATEGORIES = {
    "room", "common", "exterior", "food", "experience", "destination"
}

VALID_SEASONS = {"spring", "summer", "autumn", "winter", "any_season"}


class VisionAnalysis(BaseModel):
    """Structured output from Claude Vision analysis of a hotel photo/video frame."""

    category: str = Field(
        description="Main category: room, common, exterior, food, experience, destination"
    )
    subcategory: str = Field(
        description="Specific area: suite, terrace, pool, breakfast, spa, etc."
    )
    ambiance: list[str] = Field(
        default_factory=list,
        description="Mood tags: bright, warm, romantic, modern, art_nouveau, mediterranean, cozy, elegant, natural, colorful, etc."
    )
    season: list[str] = Field(
        default_factory=list,
        description="Best seasons: spring, summer, autumn, winter, any_season"
    )
    elements: list[str] = Field(
        default_factory=list,
        description="Visible elements: bed, sea_view, pool, terrace, furniture, etc."
    )
    ig_quality: int = Field(
        ge=1, le=10,
        description="Instagram quality score 1-10"
    )
    description_fr: str = Field(
        description="One-line French description of the image"
    )
    description_en: str = Field(
        description="One-line English description of the image"
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_CATEGORIES:
            # Best-effort mapping (handles legacy French + alt English)
            mapping = {
                "chambre": "room", "bedroom": "room",
                "commun": "common", "lobby": "common", "lounge": "common",
                "exterieur": "exterior", "outdoor": "exterior", "garden": "exterior",
                "gastronomie": "food", "restaurant": "food", "dining": "food",
                "activity": "experience", "event": "experience",
                "town": "destination", "city": "destination", "beach": "destination",
                "street": "destination", "village": "destination", "landscape": "destination",
            }
            v = mapping.get(v, v)
        return v

    @field_validator("season", mode="before")
    @classmethod
    def validate_season(cls, v: list[str]) -> list[str]:
        return [s.lower().strip() for s in v]

    @field_validator("ig_quality")
    @classmethod
    def clamp_quality(cls, v: int) -> int:
        return max(1, min(10, v))


class SceneAnalysis(BaseModel):
    """Per-scene analysis for videos."""
    scene_index: int
    start_sec: float
    end_sec: float
    frame_count: int
    analysis: VisionAnalysis


class MediaItem(BaseModel):
    """A media file from Google Drive ready for database insertion."""
    drive_file_id: str
    file_name: str
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    media_type: str = Field(description="'image' or 'video'")
    # Vision analysis fields (populated after Claude call)
    category: Optional[str] = None
    subcategory: Optional[str] = None
    ambiance: list[str] = Field(default_factory=list)
    season: list[str] = Field(default_factory=list)
    elements: list[str] = Field(default_factory=list)
    ig_quality: Optional[int] = None
    aspect_ratio: Optional[str] = None
    description_fr: Optional[str] = None
    description_en: Optional[str] = None
    # Video-specific
    duration_seconds: Optional[float] = None
    scenes: Optional[list[dict]] = None
    # Raw AI data
    analysis_raw: Optional[dict] = None
    analysis_model: Optional[str] = None
    status: str = "pending"
    error_message: Optional[str] = None
