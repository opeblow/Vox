import os
import sys
import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.utils.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Transcribe"])


class TranscribeRequest(BaseModel):
    url: str


class TranscribeResponse(BaseModel):
    status: str
    title: str
    transcript: str
    study_notes: str


@router.post("/url", response_model=TranscribeResponse)
@limiter.limit("10/minute")
async def transcribe_from_url(request: Request, body: TranscribeRequest, user: User = Depends(get_current_user)):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    ffmpeg_dir = r"C:\Users\user\AppData\Local\ffmpeg\bin"
    if os.path.isdir(ffmpeg_dir):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    try:
        from backend.services.downloader import download_audio
        download_dir = os.path.join("storage", "transcribe", str(user.id))
        os.makedirs(download_dir, exist_ok=True)
        audio_path, title = download_audio(url, download_dir)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

    try:
        if not audio_path or not os.path.exists(audio_path):
            raise HTTPException(status_code=500, detail="Downloaded audio file not found")

        from faster_whisper import WhisperModel
        logger.info("Loading Whisper model (tiny)...")
        model = WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=4)
        logger.info("Transcribing audio...")
        segments, info = model.transcribe(audio_path, beam_size=1, vad_filter=True)
        transcript = " ".join(s.text for s in segments)
        logger.info(f"Transcription done: {len(transcript)} chars")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        try:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

    try:
        from dotenv import load_dotenv
        from openai import OpenAI
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        load_dotenv(env_path)
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        system_prompt = """You are an AI assistant that transforms raw speech-to-text transcripts into high-quality study notes.

Your tasks:
1. Clean and fix grammar, remove filler words and repetitions. Make it read naturally.
2. Format into readable notes with logical paragraphs and section breaks.
3. Preserve all important content — facts, names, dates, concepts.
4. Output format:
   - First: Cleaned transcript as proper study notes with markdown headings
   - Then a "--- SUMMARY & KEY POINTS ---" divider
   - Then: Brief summary
   - Then: Bullet-point key takeaways
   - Then: Action items or questions raised"""

        logger.info("Generating study notes via AI...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Raw transcript from '{title}':\n\n{transcript}"},
            ],
            temperature=0.3,
        )
        study_notes = response.choices[0].message.content
    except Exception as e:
        logger.warning(f"Notes generation failed, returning raw transcript: {e}")
        study_notes = ""

    return TranscribeResponse(
        status="success",
        title=title,
        transcript=transcript,
        study_notes=study_notes,
    )
