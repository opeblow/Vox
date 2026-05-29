import os
import uuid
import shutil
import aiofiles
from pydantic import BaseModel
from fastapi import APIRouter, Depends, UploadFile, Request, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.services.file_validation import validate_audio_file, MAX_FILE_SIZE
from backend.services.ingest import process_audio_job
from backend.services.downloader import download_audio
from backend.utils.rate_limit import limiter


class UrlUploadRequest(BaseModel):
    url: str

router = APIRouter(tags=["Upload"])

STORAGE_DIR = "storage"
CHUNK_SIZE = 1024 * 1024


@router.post(
    "/audio",
    response_model=dict,
    responses={400: {"description": "Invalid file"}, 413: {"description": "File too large"}},
)
@limiter.limit("20/minute")
async def upload_audio(
    request: Request,
    file: UploadFile,
    user: User = Depends(get_current_user),
):
    validate_audio_file(file)

    total_size = 0
    temp_id = str(uuid.uuid4())[:8]
    user_audio_dir = os.path.join(STORAGE_DIR, "users", str(user.id), "audio", temp_id)
    os.makedirs(user_audio_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "audio.mp3")[1] or ".mp3"
    file_path = os.path.join(user_audio_dir, f"input{ext}")

    too_large = False
    async with aiofiles.open(file_path, "wb") as f:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                too_large = True
                break
            await f.write(chunk)

    if too_large:
        shutil.rmtree(user_audio_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )

    result = process_audio_job(user, file_path, file.filename or "audio.mp3")

    return {
        "status": "success",
        "message": "Audio uploaded. Processing started.",
        "job_id": result["job_id"],
        "podcast_id": result["podcast_id"],
        "filename": file.filename,
    }


@router.post(
    "/url",
    response_model=dict,
)
@limiter.limit("10/minute")
async def upload_from_url(
    request: Request,
    body: UrlUploadRequest,
    user: User = Depends(get_current_user),
):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    temp_id = str(uuid.uuid4())[:8]
    download_dir = os.path.join("storage", "users", str(user.id), "downloads")
    os.makedirs(download_dir, exist_ok=True)

    try:
        audio_path, title = download_audio(url, download_dir)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download audio: {str(e)}")

    if not os.path.exists(audio_path):
        raise HTTPException(status_code=500, detail="Downloaded audio file not found")

    result = process_audio_job(user, audio_path, f"{title}.mp3")

    return {
        "status": "success",
        "message": "Audio downloaded and processing started.",
        "job_id": result["job_id"],
        "podcast_id": result["podcast_id"],
        "filename": f"{title}.mp3",
        "source_url": url,
    }
