from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, Enum, ForeignKey, JSON, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


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


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.TRADER)
    avatar_appearance_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    agents = relationship("Agent", back_populates="owner")
    notification_preferences = relationship(
        "UserNotificationPreferences", back_populates="user",
        uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
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

    # Phase 2
    room = Column(String(50), default="day_trading")
    broker = Column(String(50), default="alpaca")
    context_file_path = Column(String(255), nullable=True)
    confidence_score = Column(Integer, default=10)
    execution_mode = Column(String(20), default="human_in_loop")
    check_frequency = Column(Integer, default=300)
    paper_trading_balance = Column(Float, default=100000.0)
    consecutive_losses = Column(Integer, default=0)
    consecutive_broker_errors = Column(Integer, default=0, nullable=False)
    grid_col = Column(Integer, default=0)
    grid_row = Column(Integer, default=0)
    use_local_llm = Column(Boolean, default=True)
    appearance_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_heartbeat = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="agents")
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

    is_paper = Column(Boolean, default=False, nullable=False)

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


class RoomLayout(Base):
    __tablename__ = "room_layouts"

    room_key = Column(String, primary_key=True)  # long_term | swing_trading | day_trading
    map_json = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class BrokerConfig(Base):
    __tablename__ = "broker_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    broker_name = Column(String(50), nullable=False, unique=True)
    connected_at = Column(DateTime, nullable=True)
    last_tested_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=False)


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    level = Column(String(20), nullable=False, default="INFO")
    message = Column(Text, nullable=False)
    extra_json = Column(JSON, nullable=True)


class PendingApproval(Base):
    __tablename__ = "pending_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(100), nullable=False, unique=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    decision_json = Column(JSON, nullable=False)
    timeout_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="waiting")


class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"
    __table_args__ = (UniqueConstraint('agent_id', 'date', name='uq_daily_snapshot_agent_date'),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    date = Column(String(10), nullable=False)          # ISO date string "YYYY-MM-DD"
    total_pnl = Column(Float, nullable=False, default=0.0)
    daily_return_pct = Column(Float, nullable=False, default=0.0)
    sharpe_ratio = Column(Float, nullable=True)        # NULL until 30 days of data
    max_drawdown = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    trade_count = Column(Integer, nullable=False, default=0)
    trades_won = Column(Integer, nullable=False, default=0)
    trades_lost = Column(Integer, nullable=False, default=0)
    portfolio_value = Column(Float, nullable=True)
    cash_balance = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    agent = relationship("Agent", backref="snapshots")


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(String(36), primary_key=True)          # UUID string
    agent_id = Column(Integer, nullable=True)          # optional; no FK constraint to allow ad-hoc backtests
    run_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    start_date = Column(String(10), nullable=False)    # "YYYY-MM-DD"
    end_date = Column(String(10), nullable=False)
    mode = Column(String(20), nullable=False, default="basic")  # "basic" | "walk_forward"
    status = Column(String(20), nullable=False, default="running")  # "running" | "done" | "failed"
    result_json = Column(JSON, nullable=True)          # NULL until done


# Import notification models at bottom to avoid circular imports
from backend.notifications.models import UserNotificationPreferences  # noqa: F401, E402
