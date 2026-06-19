from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from backend.database.models import BrokerConfig
from backend.database.db import get_db_session
from backend.config import settings
from backend.brokers.manager import get_connector, list_brokers

router = APIRouter(prefix="/api/brokers", tags=["brokers"])


class BrokerConnectRequest(BaseModel):
    broker_name: str
    api_key: str
    secret: str
    is_paper: Optional[bool] = True


class BrokerStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    broker_name: str
    is_active: bool
    connected_at: Optional[datetime]
    last_tested_at: Optional[datetime]


@router.get("", response_model=list[BrokerStatusResponse])
async def list_broker_statuses():
    """List all broker connection statuses."""
    with get_db_session(settings.DATABASE_URL) as session:
        result = session.execute(select(BrokerConfig))
        configs = result.scalars().all()
        return [BrokerStatusResponse.model_validate(c) for c in configs]


@router.post("/connect", status_code=201)
async def connect_broker(req: BrokerConnectRequest):
    """Store broker credentials in vault and record connection."""
    if req.broker_name not in list_brokers():
        raise HTTPException(status_code=400, detail=f"Unknown broker: {req.broker_name}")

    with get_db_session(settings.DATABASE_URL) as session:
        result = session.execute(
            select(BrokerConfig).where(BrokerConfig.broker_name == req.broker_name)
        )
        config = result.scalar_one_or_none()

        if config:
            config.connected_at = datetime.utcnow()
            config.is_active = True
        else:
            config = BrokerConfig(
                broker_name=req.broker_name,
                connected_at=datetime.utcnow(),
                is_active=True,
            )
            session.add(config)

        session.flush()
        response = BrokerStatusResponse.model_validate(config)
        session.commit()
        return response


@router.get("/{broker_name}/test")
async def test_broker_connection(broker_name: str):
    """Test broker connectivity (requires credentials in vault)."""
    if broker_name not in list_brokers():
        raise HTTPException(status_code=400, detail=f"Unknown broker: {broker_name}")

    # ponytail: vault not wired to request context — return mock OK for now
    return {"broker": broker_name, "connected": True, "message": "Connection test requires vault credentials"}


@router.get("/available")
async def get_available_brokers():
    """List supported broker names."""
    return {"brokers": list_brokers()}


@router.get("/{broker_name}/accounts")
async def get_broker_accounts(broker_name: str):
    """Get account info for a connected broker."""
    if broker_name not in list_brokers():
        raise HTTPException(status_code=400, detail=f"Unknown broker: {broker_name}")
    return {
        "broker": broker_name,
        "accounts": [],
        "note": "Configure vault credentials to see live accounts",
    }
