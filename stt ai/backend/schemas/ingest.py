import datetime
from typing import Optional

from pydantic import BaseModel


class UploadResponse(BaseModel):
    status: str
    message: str
    job_id: str
    filename: str


class JobStatusResponse(BaseModel):
    status: str
    job_id: str
    podcast_id: Optional[str] = None
    original_filename: Optional[str] = None
    language: Optional[str] = None
    speaker_count: Optional[int] = None
    speakers: Optional[list] = None
    error: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None


class JobListResponse(BaseModel):
    status: str
    jobs: list[JobStatusResponse]
    total: int
