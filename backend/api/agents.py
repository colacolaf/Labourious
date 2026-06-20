from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from backend.database.models import Agent, AgentStatus, Trade, Performance, TradeSide, TradeStatus, User, UserRole
from backend.database.db import get_db_session
from backend.auth.dependencies import get_current_user
from backend.config import settings

router = APIRouter(prefix="/api/agents", tags=["agents"])


# Inline Pydantic schemas (ponytail: no separate file)
class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    symbol: str = Field(..., min_length=1, max_length=20)
    exchange: Optional[str] = Field(default="binance", max_length=50)
    timeframe: Optional[str] = Field(default="1h", max_length=10)
    strategy_config: Optional[dict] = None
    risk_config: Optional[dict] = None
    is_paper_trading: Optional[bool] = True
    is_active: Optional[bool] = True
    room: Optional[str] = Field(default="day_trading", max_length=50)
    broker: Optional[str] = Field(default="alpaca", max_length=50)
    use_local_llm: Optional[bool] = True
    max_position_size: Optional[float] = 1000.0
    stop_loss_pct: Optional[float] = 2.0
    take_profit_pct: Optional[float] = 4.0


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    symbol: Optional[str] = Field(None, min_length=1, max_length=20)
    exchange: Optional[str] = Field(None, max_length=50)
    timeframe: Optional[str] = Field(None, max_length=10)
    strategy_config: Optional[dict] = None
    risk_config: Optional[dict] = None
    is_paper_trading: Optional[bool] = None
    is_active: Optional[bool] = None
    room: Optional[str] = Field(None, max_length=50)
    max_position_size: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    symbol: str
    exchange: str
    timeframe: str
    status: str
    is_active: bool
    is_paper_trading: bool
    room: str
    broker: str
    use_local_llm: bool
    max_position_size: float
    stop_loss_pct: float
    take_profit_pct: float
    total_trades: int
    winning_trades: int
    total_pnl: float
    win_rate: float
    current_drawdown: float
    consecutive_losses: int
    created_at: datetime


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    side: str
    status: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]
    opened_at: datetime


class PerformanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    period: str
    portfolio_value: float
    cash_balance: float
    total_pnl: float
    win_rate: float


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    room: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """List agents. Admins see all; traders see own agents only."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            query = select(Agent)
            role_val = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
            if role_val != UserRole.ADMIN.value:
                query = query.where(Agent.user_id == current_user.id)
            if room:
                query = query.where(Agent.room == room)
            if is_active is not None:
                query = query.where(Agent.is_active == is_active)
            result = session.execute(query)
            agents = result.scalars().all()
            return [AgentResponse.model_validate(a) for a in agents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new agent owned by current user."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            agent = Agent(
                user_id=current_user.id,
                name=agent_data.name,
                symbol=agent_data.symbol,
                exchange=agent_data.exchange or "binance",
                timeframe=agent_data.timeframe or "1h",
                strategy_config=agent_data.strategy_config,
                risk_config=agent_data.risk_config,
                is_paper_trading=agent_data.is_paper_trading if agent_data.is_paper_trading is not None else True,
                is_active=agent_data.is_active if agent_data.is_active is not None else True,
                room=agent_data.room or "day_trading",
                broker=agent_data.broker or "alpaca",
                use_local_llm=agent_data.use_local_llm if agent_data.use_local_llm is not None else True,
                max_position_size=agent_data.max_position_size or 1000.0,
                stop_loss_pct=agent_data.stop_loss_pct or 2.0,
                take_profit_pct=agent_data.take_profit_pct or 4.0,
            )
            session.add(agent)
            session.flush()
            response = AgentResponse.model_validate(agent)
            session.commit()
            return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _check_agent_access(agent: Agent, current_user: User) -> None:
    """Raise 403 if non-admin user tries to access an agent they don't own."""
    role_val = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if role_val != UserRole.ADMIN.value and agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get agent detail by ID."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            _check_agent_access(agent, current_user)
            return AgentResponse.model_validate(agent)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update agent configuration."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            _check_agent_access(agent, current_user)

            update_data = agent_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(agent, field, value)
            agent.updated_at = datetime.utcnow()

            session.add(agent)
            session.flush()
            response = AgentResponse.model_validate(agent)
            session.commit()
            return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete an agent."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            _check_agent_access(agent, current_user)
            session.delete(agent)
            session.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{agent_id}/toggle", response_model=AgentResponse)
async def toggle_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
):
    """Toggle agent is_active status."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            _check_agent_access(agent, current_user)
            agent.is_active = not agent.is_active
            session.add(agent)
            session.flush()
            response = AgentResponse.model_validate(agent)
            session.commit()
            return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{agent_id}/resume", response_model=AgentResponse)
async def resume_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
):
    """Resume agent: reset consecutive_losses and status to IDLE."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            _check_agent_access(agent, current_user)
            agent.consecutive_losses = 0
            agent.status = AgentStatus.IDLE
            session.add(agent)
            session.flush()
            response = AgentResponse.model_validate(agent)
            session.commit()
            return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{agent_id}/approve")
async def approve_trade(
    agent_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
):
    """Resolve a pending human-in-loop trade approval."""
    trade_id = data.get("trade_id")
    approved = data.get("approved", False)
    if not trade_id:
        raise HTTPException(status_code=400, detail="trade_id required")
    with get_db_session(settings.DATABASE_URL) as session:
        result = session.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        _check_agent_access(agent, current_user)
    from backend.main import _orchestrator
    if _orchestrator and hasattr(_orchestrator, "executor"):
        result = await _orchestrator.executor.approve_trade(trade_id, approved)
        return result
    return {"status": "acknowledged", "trade_id": trade_id, "approved": approved}


@router.post("/{agent_id}/update-context")
async def update_agent_context(
    agent_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
):
    """Update agent's context file content."""
    content = data.get("content", "")
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            _check_agent_access(agent, current_user)
            cfg = agent.strategy_config or {}
            cfg["context_content"] = content
            agent.strategy_config = cfg
            agent.updated_at = datetime.utcnow()
            session.add(agent)
            return {"status": "updated", "agent_id": agent_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/trades", response_model=list[TradeResponse])
async def get_agent_trades(
    agent_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get last 50 trades for agent."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            _check_agent_access(agent, current_user)

            trades_result = session.execute(
                select(Trade).where(Trade.agent_id == agent_id).order_by(Trade.opened_at.desc()).limit(50)
            )
            trades = trades_result.scalars().all()
            return [TradeResponse.model_validate(t) for t in trades]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/performance", response_model=list[PerformanceResponse])
async def get_agent_performance(
    agent_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get performance records for agent."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            _check_agent_access(agent, current_user)

            perf_result = session.execute(
                select(Performance).where(Performance.agent_id == agent_id).order_by(Performance.timestamp.desc()).limit(50)
            )
            perf = perf_result.scalars().all()
            return [PerformanceResponse.model_validate(p) for p in perf]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
