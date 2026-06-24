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


@router.get("/health/full")
async def full_health():
    from backend.config import settings
    from backend.database.db import get_db_session

    result = {
        "backend": "ok",
        "uptime_seconds": (datetime.utcnow() - _start_time).total_seconds(),
    }

    try:
        with get_db_session(settings.DATABASE_URL) as session:
            session.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception as e:
        result["db"] = f"error: {str(e)[:60]}"

    try:
        if settings.VAULT_PASSWORD:
            from backend.vault.encrypted_vault import EncryptedVault
            vault = EncryptedVault(settings.VAULT_PASSWORD)
            vault.list_keys()
            result["vault"] = "ok"
        else:
            result["vault"] = "no_password"
    except Exception as e:
        result["vault"] = f"error: {str(e)[:60]}"

    try:
        from backend.llm.config import read_config
        cfg = read_config()
        result["llm"] = cfg.provider if cfg else "not_configured"
    except Exception:
        result["llm"] = "not_configured"

    return result
