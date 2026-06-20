from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.database.db import get_session_factory
from backend.database.models import User, UserRole
from backend.auth.utils import decode_token
from backend.config import settings

security = HTTPBearer()


def _get_db() -> Session:
    """Get a DB session for auth endpoints."""
    factory = get_session_factory(settings.DATABASE_URL)
    db = factory()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(_get_db)
) -> User:
    """Dependency: extract + validate JWT, return User. Raises 401 on failure."""
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*allowed_roles):
    """Dependency factory: check user has one of the allowed roles."""
    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        # Check both UserRole enum and string value for flexibility
        user_role_value = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
        if current_user.role not in allowed_roles and user_role_value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return check_role
