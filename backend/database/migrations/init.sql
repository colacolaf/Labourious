-- Reference schema backup — auto-managed by SQLAlchemy ORM in db.py
-- This file is for human reference only; do not run directly.

CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    agent_type VARCHAR(20) NOT NULL DEFAULT 'custom',
    status VARCHAR(20) NOT NULL DEFAULT 'idle',
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL DEFAULT 'binance',
    timeframe VARCHAR(10) NOT NULL DEFAULT '1h',
    strategy_config JSON,
    risk_config JSON,
    max_position_size REAL DEFAULT 1000.0,
    stop_loss_pct REAL DEFAULT 2.0,
    take_profit_pct REAL DEFAULT 4.0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0.0,
    current_drawdown REAL DEFAULT 0.0,
    is_paper_trading BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    last_heartbeat DATETIME
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    exchange_order_id VARCHAR(100),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    entry_price REAL NOT NULL,
    exit_price REAL,
    quantity REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    pnl REAL,
    pnl_pct REAL,
    fees REAL DEFAULT 0.0,
    entry_reason TEXT,
    exit_reason TEXT,
    trade_metadata JSON,
    opened_at DATETIME NOT NULL,
    closed_at DATETIME,
    created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    timestamp DATETIME NOT NULL,
    period VARCHAR(20) NOT NULL DEFAULT 'daily',
    portfolio_value REAL NOT NULL,
    cash_balance REAL NOT NULL,
    unrealized_pnl REAL DEFAULT 0.0,
    realized_pnl REAL DEFAULT 0.0,
    total_pnl REAL DEFAULT 0.0,
    num_trades INTEGER DEFAULT 0,
    num_wins INTEGER DEFAULT 0,
    num_losses INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0.0,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    max_drawdown REAL DEFAULT 0.0,
    calmar_ratio REAL,
    metrics JSON,
    created_at DATETIME NOT NULL
);
