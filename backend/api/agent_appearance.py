from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from pydantic import BaseModel

from backend.database.models import Agent, User
from backend.database.db import get_db_session
from backend.auth.dependencies import get_current_user
from backend.config import settings

router = APIRouter(prefix="/api", tags=["appearance"])


class AppearanceSave(BaseModel):
    appearance: dict


@router.get("/agents/{agent_id}/appearance")
async def get_agent_appearance(
    agent_id: int,
    current_user: User = Depends(get_current_user),
):
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            return {"appearance": agent.appearance_json}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_id}/appearance")
async def save_agent_appearance(
    agent_id: int,
    data: AppearanceSave,
    current_user: User = Depends(get_current_user),
):
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            agent.appearance_json = data.appearance
            session.add(agent)
            session.flush()
            saved = agent.appearance_json
            session.commit()
            return {"appearance": saved}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/avatar-appearance")
async def get_user_avatar_appearance(
    current_user: User = Depends(get_current_user),
):
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(User).where(User.id == current_user.id))
            user = result.scalar_one_or_none()
            return {"appearance": user.avatar_appearance_json if user else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/user/avatar-appearance")
async def save_user_avatar_appearance(
    data: AppearanceSave,
    current_user: User = Depends(get_current_user),
):
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(User).where(User.id == current_user.id))
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user.avatar_appearance_json = data.appearance
            session.add(user)
            session.flush()
            saved = user.avatar_appearance_json
            session.commit()
            return {"appearance": saved}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
