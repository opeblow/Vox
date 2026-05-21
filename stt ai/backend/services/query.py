import os
import json
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from functools import lru_cache

from backend.models.user import User
from backend.models.job import Job
from backend.services.cache import get_cache_sync, set_cache_sync, cache_key

logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def _load_vault_texts(vault_path: str) -> tuple:
    index_path = os.path.join(vault_path, "podcast.index")
    paragraphs_path = os.path.join(vault_path, "paragraphs.txt")
    paragraphs = []
    if os.path.exists(paragraphs_path):
        with open(paragraphs_path, "r", encoding="utf-8") as f:
            paragraphs = [line.strip() for line in f if line.strip()]
    return tuple(paragraphs)


def answer_question(user: User, podcast_id: str, question: str, db: Session) -> dict:
    job = db.query(Job).filter(Job.user_id == user.id, Job.podcast_id == podcast_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Podcast vault not found")

    vault_path = os.path.join("storage", "users", str(user.id), "indices", podcast_id)
    if not os.path.exists(vault_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault index not found")

    ck = cache_key("qa", str(user.id), podcast_id, question)
    cached = get_cache_sync(ck)
    if cached:
        return json.loads(cached)

    from ml.pipelines.podcast_pipeline import PodcastPipeline

    pipeline = PodcastPipeline(use_singletons=True)

    index_path = os.path.join(vault_path, "podcast.index")
    paragraphs_path = os.path.join(vault_path, "paragraphs.txt")

    if os.path.exists(index_path):
        import faiss
        pipeline.embedder_engine.index = faiss.read_index(index_path)

    paragraphs = list(_load_vault_texts(vault_path))
    if paragraphs:
        pipeline.embedder_engine.paragraphs = paragraphs

    pipeline.qa_machine = pipeline._init_qa()
    answer = pipeline.ask_ai(question)

    chunks = pipeline.embedder_engine.search(question, k=3)

    result = {
        "status": "success",
        "answer": answer,
        "podcast_id": podcast_id,
        "sources": chunks,
    }

    try:
        set_cache_sync(ck, json.dumps(result), ttl=600)
    except Exception:
        pass

    return result
