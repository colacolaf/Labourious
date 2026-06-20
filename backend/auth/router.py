from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.models import User, UserRole
from backend.auth.schemas import UserCreate, UserLogin, UserOut, TokenResponse, TokenRefresh
from backend.auth.utils import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from backend.auth.dependencies import get_current_user, require_role, _get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=UserOut)
async def register(user_data: UserCreate, db: Session = Depends(_get_db)):
    existing = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username or email already registered")
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=UserRole.TRADER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(_get_db)):
    user = db.query(User).filter_by(email=credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "access_token": create_access_token({"sub": user.id}),
        "refresh_token": create_refresh_token({"sub": user.id}),
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh(token_data: TokenRefresh, db: Session = Depends(_get_db)):
    payload = decode_token(token_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.query(User).filter_by(id=payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {
        "access_token": create_access_token({"sub": user.id}),
        "refresh_token": token_data.refresh_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserOut])
async def list_users(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(_get_db),
):
    return [
        UserOut(id=u.id, username=u.username, email=u.email, role=u.role.value)
        for u in db.query(User).all()
    ]
