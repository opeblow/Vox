import os
import json
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.models.user import User
from backend.models.job import Job

STORAGE_DIR = "storage"


def _get_vault_path(user_id: str, podcast_id: str) -> str:
    return os.path.join(STORAGE_DIR, "users", str(user_id), "indices", str(podcast_id))


def _load_metadata(vault_path: str) -> dict:
    metadata = {}
    metadata_path = os.path.join(vault_path, "metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return metadata


def get_user_vaults(user: User, db: Session, skip: int = 0, limit: int = 50) -> dict:
    jobs = db.query(Job).filter(Job.user_id == user.id, Job.status == "completed").order_by(Job.completed_at.desc()).offset(skip).limit(limit).all()
    vaults = []
    for job in jobs:
        vault_path = _get_vault_path(str(user.id), job.podcast_id)
        metadata = _load_metadata(vault_path)

        duration = 0.0
        segments = metadata.get("segments", [])
        if segments and len(segments) > 0:
            duration = segments[-1].get("end", 0)

        sentiment = metadata.get("sentiment", {})
        show_notes = metadata.get("show_notes", {})

        vaults.append({
            "podcast_id": job.podcast_id,
            "title": job.original_filename,
            "language": metadata.get("language", job.language or ""),
            "speaker_count": metadata.get("speakers_count", int(job.speaker_count) if job.speaker_count else 0),
            "speakers": metadata.get("speakers", job.speakers or []),
            "duration_minutes": round(duration / 60, 1),
            "summary": (metadata.get("summary", "") or "")[:200],
            "created_at": str(job.created_at) if job.created_at else "",
            "has_chapters": "chapters" in metadata,
            "has_key_moments": "key_moments" in metadata,
            "has_sentiment": bool(sentiment),
            "has_show_notes": bool(show_notes),
            "sentiment": sentiment.get("overall_sentiment", "") if sentiment else "",
            "tags": show_notes.get("tags", []) if show_notes else [],
        })

    return {"status": "success", "vaults": vaults, "total": len(vaults)}


def get_vault_detail(user: User, podcast_id: str, db: Session) -> dict:
    job = db.query(Job).filter(Job.user_id == user.id, Job.podcast_id == podcast_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault not found")

    vault_path = _get_vault_path(str(user.id), podcast_id)
    metadata = _load_metadata(vault_path)

    return {
        "status": "success",
        "podcast_id": podcast_id,
        "summary": metadata.get("summary"),
        "language": metadata.get("language"),
        "speakers": metadata.get("speakers"),
        "chapters": metadata.get("chapters"),
        "key_moments": metadata.get("key_moments"),
        "transcript": metadata.get("transcript"),
        "segments": metadata.get("segments"),
        "sentiment": metadata.get("sentiment"),
        "show_notes": metadata.get("show_notes"),
    }


def get_vault_summary(user: User, podcast_id: str, db: Session) -> dict:
    detail = get_vault_detail(user, podcast_id, db)
    return {
        "status": "success",
        "podcast_id": podcast_id,
        "summary": detail.get("summary", "No summary available"),
    }


def get_vault_transcript(user: User, podcast_id: str, db: Session) -> dict:
    detail = get_vault_detail(user, podcast_id, db)
    segments = detail.get("segments", [])
    speaker_transcript = "\n".join([s.get("labeled_text", s.get("text", "")) for s in segments])
    full_text = " ".join([s.get("text", "") for s in segments])
    return {
        "status": "success",
        "podcast_id": podcast_id,
        "speaker_transcript": speaker_transcript,
        "full_text": full_text,
        "segment_count": len(segments),
    }


def get_vault_sentiment(user: User, podcast_id: str, db: Session) -> dict:
    detail = get_vault_detail(user, podcast_id, db)
    sentiment = detail.get("sentiment", {})
    if not sentiment:
        return {"status": "success", "podcast_id": podcast_id, "sentiment": None}
    return {
        "status": "success",
        "podcast_id": podcast_id,
        "sentiment": sentiment,
    }


def get_vault_show_notes(user: User, podcast_id: str, db: Session) -> dict:
    detail = get_vault_detail(user, podcast_id, db)
    show_notes = detail.get("show_notes", {})
    if not show_notes:
        return {"status": "success", "podcast_id": podcast_id, "show_notes": None}
    return {
        "status": "success",
        "podcast_id": podcast_id,
        "show_notes": show_notes,
    }


def get_vault_clips(user: User, podcast_id: str, db: Session) -> dict:
    detail = get_vault_detail(user, podcast_id, db)
    key_moments = detail.get("key_moments", [])
    if not key_moments:
        return {"status": "success", "podcast_id": podcast_id, "clips": []}

    vault_path = _get_vault_path(str(user.id), podcast_id)
    audio_dir = os.path.join(STORAGE_DIR, "users", str(user.id), "audio", podcast_id)
    audio_files = []
    if os.path.exists(audio_dir):
        audio_files = [f for f in os.listdir(audio_dir) if f.startswith("input")]

    if not audio_files:
        return {"status": "success", "podcast_id": podcast_id, "clips": [], "note": "Audio file not found for clip extraction"}

    audio_path = os.path.join(audio_dir, audio_files[0])
    clips_dir = os.path.join(vault_path, "clips")

    from ml.features.clip_generator import ClipGenerator
    clips = ClipGenerator.extract_key_moment_clips(audio_path, key_moments, clips_dir)

    return {
        "status": "success",
        "podcast_id": podcast_id,
        "clips": clips,
    }
