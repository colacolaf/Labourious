from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    message: str
    timestamp: str


class AgentResponse(BaseModel):
    id: int
    name: str
    agent_type: str
    status: str
    symbol: str
    exchange: str
    is_active: bool
    is_paper_trading: bool
    total_pnl: float
    win_rate: float
    created_at: datetime

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    id: int
    agent_id: int
    symbol: str
    side: str
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    error: bool = True
    message: str
    code: str
    timestamp: datetime
