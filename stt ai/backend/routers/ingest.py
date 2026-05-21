from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.ingest import JobStatusResponse, JobListResponse
from backend.services.ingest import get_job_status, get_user_jobs

router = APIRouter(tags=["Ingest"])


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = get_job_status(job_id, user, db)
    return JobStatusResponse(**result)


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = get_user_jobs(user, db, skip=skip, limit=limit)
    return JobListResponse(**result)
