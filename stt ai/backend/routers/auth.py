from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.schemas.user import UserRegister, UserLogin, UserResponse, Token
from backend.services.auth import register_user, login_user
from backend.utils.rate_limit import limiter
from backend.config import settings

router = APIRouter(tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    responses={400: {"description": "User exists"}},
)
@limiter.limit("20/minute")
def register(request: Request, user: UserRegister, db: Session = Depends(get_db)):
    return register_user(db, user)


@router.post(
    "/login",
    response_model=Token,
    responses={401: {"description": "Invalid credentials"}},
)
@limiter.limit("30/minute")
def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    return login_user(db, user)


@router.post(
    "/logout",
    response_model=dict,
    dependencies=[Depends(get_current_user)],
)
def logout():
    return {"message": "Successfully logged out"}
