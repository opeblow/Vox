from typing import Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    podcast_id: str
    question: str


class QueryResponse(BaseModel):
    status: str
    answer: str
    podcast_id: str
    sources: Optional[list[str]] = None
