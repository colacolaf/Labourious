export const APP_NAME = 'Labourious';
export const APP_VERSION = '0.1.0';

export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';
export const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://127.0.0.1:8000';

export const AGENT_STATUS = {
  IDLE: 'idle',
  RUNNING: 'running',
  PAUSED: 'paused',
  ERROR: 'error',
  STOPPED: 'stopped',
};

export const AGENT_TYPE = {
  MOMENTUM: 'momentum',
  MEAN_REVERSION: 'mean_reversion',
  ARBITRAGE: 'arbitrage',
  SCALPER: 'scalper',
  SWING: 'swing',
  CUSTOM: 'custom',
};

export const TRADE_STATUS = {
  OPEN: 'open',
  CLOSED: 'closed',
  CANCELLED: 'cancelled',
  PENDING: 'pending',
};

export const TRADE_SIDE = {
  BUY: 'buy',
  SELL: 'sell',
};

export const STATUS_COLORS = {
  [AGENT_STATUS.IDLE]: 'var(--color-agent-idle)',
  [AGENT_STATUS.RUNNING]: 'var(--color-agent-running)',
  [AGENT_STATUS.PAUSED]: 'var(--color-agent-paused)',
  [AGENT_STATUS.ERROR]: 'var(--color-agent-error)',
  [AGENT_STATUS.STOPPED]: 'var(--color-agent-stopped)',
};

export const CHART_COLORS = {
  primary: '#00ff88',
  secondary: '#00d4ff',
  tertiary: '#7c3aed',
  warning: '#ffb020',
  danger: '#ff4444',
  grid: '#1e1e3a',
  tooltip: '#1a1a2e',
};

export const TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'];

export const SUPPORTED_EXCHANGES = [
  { id: 'binance', name: 'Binance', testnet: true },
  { id: 'bybit', name: 'Bybit', testnet: true },
  { id: 'coinbase', name: 'Coinbase', testnet: false },
  { id: 'kraken', name: 'Kraken', testnet: false },
];

export const POLL_INTERVALS = {
  AGENTS: 5_000,
  PORTFOLIO: 10_000,
  TRADES: 5_000,
  HEALTH: 30_000,
};

export const ROUTES = {
  DASHBOARD: '/',
  AGENTS: '/agents',
  AGENT_DETAIL: '/agents/:id',
  TRADES: '/trades',
  PERFORMANCE: '/performance',
  VAULT: '/vault',
  SETTINGS: '/settings',
};

export const LOCAL_STORAGE_KEYS = {
  THEME: 'lab_theme',
  SIDEBAR_COLLAPSED: 'lab_sidebar_collapsed',
  SELECTED_EXCHANGE: 'lab_exchange',
};
