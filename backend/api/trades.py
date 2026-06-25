import csv
import io
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, or_
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from backend.database.models import Trade, TradeStatus, TradeSide, Agent, User
from backend.database.db import get_db_session
from backend.auth.dependencies import get_current_user
from backend.config import settings

router = APIRouter(prefix="/api/trades", tags=["trades"])


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    symbol: str
    side: str
    status: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]
    pnl_pct: Optional[float]
    fees: float
    entry_reason: Optional[str]
    exit_reason: Optional[str]
    opened_at: datetime
    closed_at: Optional[datetime]


@router.get("", response_model=list[TradeResponse])
async def list_trades(
    agent_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
):
    """List trades with optional filters."""
    with get_db_session(settings.DATABASE_URL) as session:
        query = select(Trade).order_by(Trade.opened_at.desc()).limit(limit)
        if agent_id:
            query = query.where(Trade.agent_id == agent_id)
        if status:
            query = query.where(Trade.status == status)
        if symbol:
            query = query.where(Trade.symbol == symbol)
        result = session.execute(query)
        trades = result.scalars().all()
        return [TradeResponse.model_validate(t) for t in trades]


@router.get("/export")
async def export_trades_csv(
    agent_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Export trades as CSV scoped to current user's agents. Legacy agents (user_id IS NULL) included."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "agent_id", "symbol", "side", "status", "entry_price",
        "exit_price", "quantity", "pnl", "pnl_pct", "fees", "is_paper",
        "entry_reason", "exit_reason", "opened_at", "closed_at",
    ])

    with get_db_session(settings.DATABASE_URL) as session:
        query = (
            select(Trade)
            .join(Agent, Trade.agent_id == Agent.id)
            .where(or_(Agent.user_id == current_user.id, Agent.user_id.is_(None)))
            .order_by(Trade.opened_at.desc())
        )
        if agent_id:
            query = query.where(Trade.agent_id == agent_id)
        result = session.execute(query)
        trades = result.scalars().all()
        for t in trades:
            writer.writerow([
                t.id, t.agent_id, t.symbol,
                t.side.value if hasattr(t.side, 'value') else t.side,
                t.status.value if hasattr(t.status, 'value') else t.status,
                t.entry_price, t.exit_price, t.quantity, t.pnl, t.pnl_pct,
                t.fees, t.is_paper,
                t.entry_reason or "", t.exit_reason or "",
                t.opened_at.isoformat() if t.opened_at else "",
                t.closed_at.isoformat() if t.closed_at else "",
            ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=labourious_trades.csv"},
    )


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(trade_id: int):
    """Get trade by ID."""
    with get_db_session(settings.DATABASE_URL) as session:
        result = session.execute(select(Trade).where(Trade.id == trade_id))
        trade = result.scalar_one_or_none()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        return TradeResponse.model_validate(trade)
