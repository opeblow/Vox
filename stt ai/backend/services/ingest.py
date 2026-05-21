import os
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.models.job import Job
from backend.models.user import User
from backend.database import SessionLocal

STORAGE_DIR = "storage"
_executor = ThreadPoolExecutor(max_workers=4)


def _run_pipeline_in_background(job_id: str, user_id: str, podcast_id: str, audio_path: str):
    import sys
    import logging
    import traceback

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = "processing"
        db.commit()

        sys.path.insert(0, os.path.abspath("."))
        from ml.pipelines.podcast_pipeline import PodcastPipeline

        pipeline = PodcastPipeline(use_singletons=True)
        result = pipeline.execute(str(user_id), podcast_id, audio_path)

        job.status = "completed"
        job.language = result.get("language", "")
        job.speaker_count = str(result.get("speaker_count", 0))
        job.speakers = result.get("speakers", [])
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Job {job_id} completed successfully")
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        traceback.print_exc()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(e)[:500]
            db.commit()
    finally:
        db.close()


def process_audio_job(user: User, file_path: str, original_filename: str) -> dict:
    podcast_id = str(uuid.uuid4())[:8]
    job_id = str(uuid.uuid4())

    db: Session = SessionLocal()
    try:
        job = Job(
            id=uuid.UUID(job_id),
            user_id=user.id,
            podcast_id=podcast_id,
            original_filename=original_filename,
            status="pending",
        )
        db.add(job)
        db.commit()

        _executor.submit(
            _run_pipeline_in_background,
            job_id, str(user.id), podcast_id, file_path,
        )

        return {"status": "success", "job_id": job_id, "podcast_id": podcast_id, "filename": original_filename}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        db.close()


def get_job_status(job_id: str, user: User, db: Session) -> dict:
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {
        "status": job.status,
        "job_id": str(job.id),
        "podcast_id": job.podcast_id,
        "original_filename": job.original_filename,
        "language": job.language,
        "speaker_count": int(job.speaker_count) if job.speaker_count else 0,
        "speakers": job.speakers or [],
        "error": job.error,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }


def get_user_jobs(user: User, db: Session, skip: int = 0, limit: int = 50) -> dict:
    jobs = db.query(Job).filter(Job.user_id == user.id).order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    job_list = []
    for job in jobs:
        job_list.append({
            "status": job.status,
            "job_id": str(job.id),
            "podcast_id": job.podcast_id,
            "original_filename": job.original_filename,
            "language": job.language,
            "speaker_count": int(job.speaker_count) if job.speaker_count else 0,
            "speakers": job.speakers or [],
            "error": job.error,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
        })
    return {"status": "success", "jobs": job_list, "total": len(job_list)}
