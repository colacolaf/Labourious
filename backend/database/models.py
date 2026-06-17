from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, Enum, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class AgentType(str, enum.Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    ARBITRAGE = "arbitrage"
    SCALPER = "scalper"
    SWING = "swing"
    CUSTOM = "custom"


class TradeStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    PENDING = "pending"


class TradeSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    agent_type = Column(Enum(AgentType), nullable=False, default=AgentType.CUSTOM)
    status = Column(Enum(AgentStatus), nullable=False, default=AgentStatus.IDLE)

    symbol = Column(String(20), nullable=False)
    exchange = Column(String(50), nullable=False, default="binance")
    timeframe = Column(String(10), nullable=False, default="1h")

    strategy_config = Column(JSON, nullable=True)
    risk_config = Column(JSON, nullable=True)

    max_position_size = Column(Float, default=1000.0)
    stop_loss_pct = Column(Float, default=2.0)
    take_profit_pct = Column(Float, default=4.0)

    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    current_drawdown = Column(Float, default=0.0)

    is_paper_trading = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_heartbeat = Column(DateTime, nullable=True)

    trades = relationship("Trade", back_populates="agent", cascade="all, delete-orphan")
    performance = relationship("Performance", back_populates="agent", cascade="all, delete-orphan")

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, status={self.status})>"


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)

    exchange_order_id = Column(String(100), nullable=True)
    symbol = Column(String(20), nullable=False)
    side = Column(Enum(TradeSide), nullable=False)
    status = Column(Enum(TradeStatus), nullable=False, default=TradeStatus.PENDING)

    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)

    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    pnl = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    fees = Column(Float, default=0.0)

    entry_reason = Column(Text, nullable=True)
    exit_reason = Column(Text, nullable=True)
    trade_metadata = Column(JSON, nullable=True)

    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    agent = relationship("Agent", back_populates="trades")

    @property
    def duration_seconds(self) -> float | None:
        if self.closed_at and self.opened_at:
            return (self.closed_at - self.opened_at).total_seconds()
        return None

    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, symbol={self.symbol}, side={self.side}, status={self.status})>"


class Performance(Base):
    __tablename__ = "performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    period = Column(String(20), nullable=False, default="daily")

    portfolio_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)

    num_trades = Column(Integer, default=0)
    num_wins = Column(Integer, default=0)
    num_losses = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)

    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, default=0.0)
    calmar_ratio = Column(Float, nullable=True)

    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    agent = relationship("Agent", back_populates="performance")

    def __repr__(self) -> str:
        return f"<Performance(id={self.id}, agent_id={self.agent_id}, period={self.period})>"
