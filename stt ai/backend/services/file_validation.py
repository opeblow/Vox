from fastapi import UploadFile, HTTPException, status

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".mpeg", ".mpg", ".ogg", ".m4a", ".flac"}
MAX_FILE_SIZE = 500 * 1024 * 1024


def validate_audio_file(file: UploadFile) -> None:
    filename = file.filename or ""
    if not filename or "." not in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename has no extension"
        )
    ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )
