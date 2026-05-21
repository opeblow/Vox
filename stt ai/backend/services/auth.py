from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.schemas.user import UserRegister, UserLogin, Token, UserResponse
from backend.utils.security import hash_password, verify_password, create_access_token, decode_token


def register_user(db: Session, user: UserRegister) -> UserResponse:
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    hashed_password = hash_password(user.password)
    new_user = User(email=user.email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        plan=new_user.plan,
        created_at=new_user.created_at,
    )


def login_user(db: Session, user: UserLogin) -> Token:
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not db_user.is_active or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": db_user.email})
    return Token(access_token=access_token, token_type="bearer")


def get_user_from_token(token: str) -> User | None:
    from backend.database import SessionLocal
    payload = decode_token(token)
    if payload is None:
        return None
    email = payload.get("sub")
    if email is None:
        return None
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        return user
    finally:
        db.close()
