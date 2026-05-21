from typing import Optional
from pydantic import BaseModel


class VaultSummary(BaseModel):
    podcast_id: str
    title: str
    language: str
    speaker_count: int
    speakers: list
    duration_minutes: float
    summary: str
    created_at: str
    has_chapters: bool
    has_key_moments: bool
    has_sentiment: bool = False
    has_show_notes: bool = False
    sentiment: str = ""
    tags: list = []


class VaultListResponse(BaseModel):
    status: str
    vaults: list[VaultSummary]
    total: int


class VaultDetailResponse(BaseModel):
    status: str
    podcast_id: str
    summary: Optional[str] = None
    language: Optional[str] = None
    speakers: Optional[list] = None
    chapters: Optional[list] = None
    key_moments: Optional[list] = None
    transcript: Optional[str] = None
    segments: Optional[list] = None
    sentiment: Optional[dict] = None
    show_notes: Optional[dict] = None
