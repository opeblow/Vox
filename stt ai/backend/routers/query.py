from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.query import QueryRequest, QueryResponse
from backend.services.query import answer_question

router = APIRouter(tags=["Query"])


@router.post(
    "/ask",
    response_model=QueryResponse,
)
def ask_question(
    query: QueryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = answer_question(user, query.podcast_id, query.question, db)
    return QueryResponse(**result)
