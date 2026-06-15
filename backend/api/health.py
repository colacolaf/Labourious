import sys
import platform
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

router = APIRouter(prefix="/api", tags=["health"])

_start_time = datetime.utcnow()


@router.get("/health")
async def health_check():
    uptime = (datetime.utcnow() - _start_time).total_seconds()
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": uptime,
        "version": "0.1.0",
        "python": sys.version,
        "platform": platform.system(),
    }


@router.get("/health/db")
async def db_health():
    from backend.config import settings
    from backend.database.db import get_db_session

    try:
        with get_db_session(settings.DATABASE_URL) as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "detail": str(e)}
