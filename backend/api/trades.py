import csv
import io
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from backend.database.models import Trade, TradeStatus, TradeSide
from backend.database.db import get_db_session
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
async def export_trades_csv(agent_id: Optional[int] = Query(None)):
    """Export trades as CSV."""
    with get_db_session(settings.DATABASE_URL) as session:
        query = select(Trade).order_by(Trade.opened_at.desc())
        if agent_id:
            query = query.where(Trade.agent_id == agent_id)
        result = session.execute(query)
        trades = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "agent_id", "symbol", "side", "status", "entry_price",
                     "exit_price", "quantity", "pnl", "pnl_pct", "opened_at", "closed_at"])
    for t in trades:
        writer.writerow([t.id, t.agent_id, t.symbol, t.side, t.status, t.entry_price,
                         t.exit_price, t.quantity, t.pnl, t.pnl_pct, t.opened_at, t.closed_at])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trades.csv"},
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
