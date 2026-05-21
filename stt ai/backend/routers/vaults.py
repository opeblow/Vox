from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.vault import VaultListResponse, VaultDetailResponse
from backend.services.vault import (
    get_user_vaults, get_vault_detail, get_vault_summary,
    get_vault_transcript, get_vault_sentiment, get_vault_show_notes, get_vault_clips,
)
from ml.models.export import ExportEngine

router = APIRouter(tags=["Vaults"])


@router.get("", response_model=VaultListResponse)
def list_vaults(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = get_user_vaults(user, db, skip=skip, limit=limit)
    return VaultListResponse(**result)


@router.get("/{podcast_id}", response_model=VaultDetailResponse)
def get_vault(podcast_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = get_vault_detail(user, podcast_id, db)
    return VaultDetailResponse(**result)


@router.get("/{podcast_id}/summary", response_model=dict)
def get_summary(podcast_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_vault_summary(user, podcast_id, db)


@router.get("/{podcast_id}/transcript", response_model=dict)
def get_transcript(podcast_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_vault_transcript(user, podcast_id, db)


@router.get("/{podcast_id}/sentiment", response_model=dict)
def get_sentiment(podcast_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_vault_sentiment(user, podcast_id, db)


@router.get("/{podcast_id}/show-notes", response_model=dict)
def get_show_notes(podcast_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_vault_show_notes(user, podcast_id, db)


@router.get("/{podcast_id}/clips", response_model=dict)
def get_clips(podcast_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_vault_clips(user, podcast_id, db)


@router.get("/{podcast_id}/export/srt", response_class=PlainTextResponse)
def export_srt(podcast_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    detail = get_vault_detail(user, podcast_id, db)
    segments = detail.get("segments", [])
    return ExportEngine.to_srt(segments)


@router.get("/{podcast_id}/export/vtt", response_class=PlainTextResponse)
def export_vtt(podcast_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    detail = get_vault_detail(user, podcast_id, db)
    segments = detail.get("segments", [])
    return ExportEngine.to_vtt(segments)


@router.get("/{podcast_id}/export/markdown", response_class=PlainTextResponse)
def export_markdown(podcast_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    detail = get_vault_detail(user, podcast_id, db)
    segments = detail.get("segments", [])
    summary = detail.get("summary", "")
    chapters = detail.get("chapters", [])
    return ExportEngine.to_markdown(segments, summary=summary, chapters=chapters)
