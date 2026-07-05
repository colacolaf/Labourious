from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from datetime import datetime
from pydantic import BaseModel

from backend.database.models import RoomLayout, User
from backend.database.db import get_db_session
from backend.auth.dependencies import get_current_user
from backend.config import settings

router = APIRouter(prefix="/api/room-layouts", tags=["room-layouts"])


class RoomLayoutSave(BaseModel):
    map_json: dict


@router.get("/{room_key}")
async def get_room_layout(
    room_key: str,
    current_user: User = Depends(get_current_user),
):
    """Return the saved custom layout for a room, or {"custom": false} if none exists."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(RoomLayout).where(RoomLayout.room_key == room_key))
            layout = result.scalar_one_or_none()
            if not layout:
                return {"custom": False}
            return {"custom": True, "map_json": layout.map_json}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{room_key}")
async def save_room_layout(
    room_key: str,
    data: RoomLayoutSave,
    current_user: User = Depends(get_current_user),
):
    """Upsert the custom layout for a room."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(RoomLayout).where(RoomLayout.room_key == room_key))
            layout = result.scalar_one_or_none()
            if layout:
                layout.map_json = data.map_json
                layout.updated_at = datetime.utcnow()
            else:
                layout = RoomLayout(room_key=room_key, map_json=data.map_json)
            session.add(layout)
            session.flush()
            saved = layout.map_json
            session.commit()
            return {"map_json": saved}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{room_key}", status_code=204)
async def reset_room_layout(
    room_key: str,
    current_user: User = Depends(get_current_user),
):
    """Delete the custom layout for a room, resetting it to the bundled default."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(RoomLayout).where(RoomLayout.room_key == room_key))
            layout = result.scalar_one_or_none()
            if layout:
                session.delete(layout)
                session.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
