import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User
from backend.services.auth import get_user_from_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/transcribe/{podcast_id}")
async def ws_transcribe(websocket: WebSocket, podcast_id: str, token: str = ""):
    await websocket.accept()
    logger.info(f"[WS] Transcription client connected for {podcast_id}")

    try:
        user = get_user_from_token(token)
        if not user:
            await websocket.send_json({"error": "Invalid token"})
            await websocket.close(code=4001)
            return

        from backend.services.vault import get_vault_detail
        db: Session = next(get_db())
        try:
            detail = get_vault_detail(user, podcast_id, db)
            segments = detail.get("segments", [])

            for seg in segments:
                await websocket.send_json({
                    "type": "transcript",
                    "start": seg["start"],
                    "end": seg["end"],
                    "speaker": seg.get("speaker", "UNKNOWN"),
                    "text": seg.get("text", ""),
                    "labeled_text": seg.get("labeled_text", ""),
                })
                await asyncio.sleep(0.01)

            summary = detail.get("summary", "")
            await websocket.send_json({
                "type": "summary",
                "content": summary,
            })

            chapters = detail.get("chapters", [])
            await websocket.send_json({
                "type": "chapters",
                "chapters": chapters,
            })

            key_moments = detail.get("key_moments", [])
            await websocket.send_json({
                "type": "key_moments",
                "moments": key_moments,
            })

            sentiment = detail.get("sentiment", {})
            if sentiment:
                await websocket.send_json({
                    "type": "sentiment",
                    "data": sentiment,
                })

            await websocket.send_json({"type": "complete", "podcast_id": podcast_id})

        finally:
            db.close()

    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected from {podcast_id}")
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
