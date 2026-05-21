import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Comparison"])


@router.post("/podcasts", response_model=dict)
def compare_podcasts(
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    podcast_ids = payload.get("podcast_ids", [])
    if len(podcast_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 podcast IDs")

    from backend.services.vault import get_vault_detail

    podcasts = []
    for pid in podcast_ids[:5]:
        try:
            detail = get_vault_detail(user, pid, db)
            podcasts.append(detail)
        except HTTPException:
            continue

    if len(podcasts) < 2:
        raise HTTPException(status_code=404, detail="Could not find enough valid podcasts")

    from ml.features.comparison import PodcastComparator

    comparator = PodcastComparator()
    result = comparator.compare(podcasts[0], podcasts[1])

    return {
        "status": "success",
        "podcast_a": podcast_ids[0],
        "podcast_b": podcast_ids[1],
        "comparison": result,
    }


@router.get("/similarity", response_model=dict)
def similarity_search(
    podcast_id_a: str,
    podcast_id_b: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from backend.services.vault import get_vault_detail

    detail_a = get_vault_detail(user, podcast_id_a, db)
    detail_b = get_vault_detail(user, podcast_id_b, db)

    segments_a = detail_a.get("segments", [])
    segments_b = detail_b.get("segments", [])

    text_a = " ".join(s.get("text", "") for s in segments_a)[:2000]
    text_b = " ".join(s.get("text", "") for s in segments_b)[:2000]

    from sentence_transformers import SentenceTransformer
    import numpy as np

    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb_a = model.encode([text_a])
    emb_b = model.encode([text_b])
    similarity = float(np.dot(emb_a, emb_b.T) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b) + 1e-10))

    return {
        "status": "success",
        "podcast_a": podcast_id_a,
        "podcast_b": podcast_id_b,
        "cosine_similarity": round(similarity, 4),
    }
