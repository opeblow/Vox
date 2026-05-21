import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, UploadFile, Request, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.services.file_validation import validate_audio_file, MAX_FILE_SIZE
from backend.services.ingest import process_audio_job
from backend.utils.rate_limit import limiter

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

    async with aiofiles.open(file_path, "wb") as f:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                await f.close()
                os.remove(file_path)
                os.rmdir(user_audio_dir)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
                )
            await f.write(chunk)

    result = process_audio_job(user, file_path, file.filename or "audio.mp3")

    return {
        "status": "success",
        "message": "Audio uploaded. Processing started.",
        "job_id": result["job_id"],
        "podcast_id": result["podcast_id"],
        "filename": file.filename,
    }
