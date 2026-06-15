Labourious API Reference
Complete REST and WebSocket API documentation for Labourious backend.

API Overview
Base URL: http://localhost:8000
Default Ports:

Frontend: http://localhost:3000
Backend: http://localhost:8000
WebSocket: ws://localhost:8000/ws

Response Format: JSON
Authentication: None (local machine only)
CORS: Enabled for localhost:3000

Error Response Format
All error responses follow this format:
json{
  "error": true,
  "message": "Human readable error description",
  "code": "ERROR_CODE",
  "timestamp": "2024-06-13T14:32:45.123Z"
}
Common Error Codes:

VALIDATION_ERROR (400): Invalid request parameters
NOT_FOUND (404): Agent/trade/broker doesn't exist
DATABASE_ERROR (500): Database operation failed
BROKER_CONNECTION_ERROR (500): Broker API unreachable
LLM_ERROR (500): LLM service error
VAULT_ERROR (500): Encryption/vault error


HTTP Status Codes
CodeMeaning200Success201Created400Bad Request (validation error)404Not Found500Server Error503Service Unavailable

Agent Endpoints (/api/agents)
GET /api/agents
List all agents
Parameters:

room (optional): Filter by room (day_trading, swing_trading, long_term)
enabled (optional): Filter by status (true/false)
skip (optional): Pagination offset (default: 0)
limit (optional): Number of results (default: 50, max: 100)

Response:
json{
  "agents": [
    {
      "id": "agent_abc123",
      "name": "BTC Momentum Trader",
      "room": "day_trading",
      "asset": "BTC/USD",
      "broker": "kraken",
      "enabled": true,
      "p_and_l": 1250.50,
      "p_and_l_percent": 6.25,
      "confidence_score": 72,
      "status": "active",
      "created_at": "2024-06-10T09:30:00Z",
      "updated_at": "2024-06-13T14:32:00Z"
    }
  ],
  "total": 11,
  "pages": 1
}
Example:
bashcurl http://localhost:8000/api/agents
curl http://localhost:8000/api/agents?room=day_trading&enabled=true

POST /api/agents
Create new agent
Request Body:
json{
  "name": "My New Agent",
  "room": "swing_trading",
  "asset": "AAPL",
  "broker": "interactive_brokers",
  "enabled": true,
  "context_file_content": "AGENT NAME: My New Agent...",
  "config": {
    "execution_mode": "human_in_loop",
    "position_size_percent": 2.0,
    "max_concurrent_positions": 3,
    "check_frequency": "daily",
    "paper_trading": true
  }
}
Response (201 Created):
json{
  "id": "agent_abc123",
  "name": "My New Agent",
  "status": "created",
  "message": "Agent created successfully, starting in paper trading mode"
}
Example:
bashcurl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{"name":"Energy Trader","room":"sector_trading","asset":"XLE","broker":"kraken",...}'

GET /api/agents/{id}
Get agent details
Parameters:

id (path): Agent ID

Response:
json{
  "id": "agent_abc123",
  "name": "BTC Momentum Trader",
  "room": "day_trading",
  "asset": "BTC/USD",
  "broker": "kraken",
  "enabled": true,
  "config": {
    "execution_mode": "human_in_loop",
    "position_size_percent": 1.5,
    "max_position_size": 2000,
    "max_concurrent_positions": 2,
    "check_frequency": "every_5_minutes",
    "paper_trading": true,
    "approval_timeout_seconds": 30
  },
  "context_file_path": "contexts/btc_momentum.txt",
  "p_and_l": 1250.50,
  "p_and_l_percent": 6.25,
  "confidence_score": 72,
  "status": "active",
  "created_at": "2024-06-10T09:30:00Z",
  "updated_at": "2024-06-13T14:32:00Z",
  "performance": {
    "total_trades": 18,
    "winning_trades": 12,
    "losing_trades": 6,
    "win_rate": 0.667,
    "average_winner": 185.50,
    "average_loser": -52.30,
    "sharpe_ratio": 1.2,
    "max_drawdown": -8.5
  }
}
Example:
bashcurl http://localhost:8000/api/agents/agent_abc123

PUT /api/agents/{id}
Update agent configuration
Request Body:
json{
  "name": "Updated Agent Name",
  "enabled": true,
  "config": {
    "execution_mode": "autonomous",
    "position_size_percent": 2.5,
    "check_frequency": "every_10_minutes"
  }
}
Response:
json{
  "id": "agent_abc123",
  "status": "updated",
  "message": "Agent configuration updated successfully"
}

DELETE /api/agents/{id}
Delete agent
Response:
json{
  "id": "agent_abc123",
  "status": "deleted",
  "message": "Agent deleted successfully"
}

POST /api/agents/{id}/approve
Approve pending trade (human-in-loop mode)
Request Body:
json{
  "trade_id": "trade_xyz789",
  "approved": true
}
Response:
json{
  "trade_id": "trade_xyz789",
  "agent_id": "agent_abc123",
  "status": "executed",
  "message": "Trade executed successfully",
  "order_id": "order_12345"
}
Example (approve):
bashcurl -X POST http://localhost:8000/api/agents/agent_abc123/approve \
  -H "Content-Type: application/json" \
  -d '{"trade_id":"trade_xyz789","approved":true}'
Example (reject):
bashcurl -X POST http://localhost:8000/api/agents/agent_abc123/approve \
  -H "Content-Type: application/json" \
  -d '{"trade_id":"trade_xyz789","approved":false}'

POST /api/agents/{id}/toggle
Enable or disable agent
Request Body:
json{
  "enabled": false
}
Response:
json{
  "agent_id": "agent_abc123",
  "enabled": false,
  "status": "toggled",
  "message": "Agent disabled"
}

POST /api/agents/{id}/update-context
Update agent's context file
Request Body:
json{
  "context_file_content": "AGENT NAME: Updated Agent\nROOM: day_trading\n..."
}
Response:
json{
  "agent_id": "agent_abc123",
  "status": "context_updated",
  "message": "Context file updated successfully"
}

GET /api/agents/{id}/trades
Get agent's trade history
Parameters:

id (path): Agent ID
page (optional): Page number (default: 1)
limit (optional): Results per page (default: 20, max: 100)
status (optional): Filter by status (open, closed, rejected)
symbol (optional): Filter by symbol

Response:
json{
  "trades": [
    {
      "id": "trade_abc123",
      "agent_id": "agent_abc123",
      "symbol": "BTC/USD",
      "side": "BUY",
      "quantity": 0.05,
      "entry_price": 45230.50,
      "entry_time": "2024-06-13T10:15:00Z",
      "exit_price": 46100.00,
      "exit_time": "2024-06-13T11:30:00Z",
      "p_and_l": 435.25,
      "p_and_l_percent": 1.92,
      "reason": "Price broke above 20-day MA, RSI < 70",
      "status": "closed",
      "created_at": "2024-06-13T10:15:00Z"
    }
  ],
  "total": 18,
  "pages": 1
}

GET /api/agents/{id}/performance
Get agent's performance metrics
Parameters:

id (path): Agent ID
timeframe (optional): day, week, month, all (default: all)

Response:
json{
  "agent_id": "agent_abc123",
  "timeframe": "all",
  "performance": {
    "total_return": 1250.50,
    "total_return_percent": 6.25,
    "total_trades": 18,
    "winning_trades": 12,
    "losing_trades": 6,
    "win_rate": 0.667,
    "average_winner": 185.50,
    "average_loser": -52.30,
    "largest_winner": 450.00,
    "largest_loser": -125.00,
    "sharpe_ratio": 1.2,
    "max_drawdown": -8.5,
    "recovery_time_days": 12,
    "consecutive_wins": 4,
    "consecutive_losses": 2
  }
}

Broker Endpoints (/api/brokers)
POST /api/brokers/connect
Connect new broker account
Request Body:
json{
  "broker_name": "kraken",
  "api_key": "your_api_key_here",
  "api_secret": "your_api_secret_here",
  "account_id": "optional_account_id",
  "extra_config": {
    "2fa_code": "optional"
  }
}
Response (201 Created):
json{
  "broker_id": "broker_kraken_001",
  "broker_name": "kraken",
  "status": "connected",
  "account_balance": 50000.00,
  "currency": "USD",
  "message": "Successfully connected to Kraken"
}
Example:
bashcurl -X POST http://localhost:8000/api/brokers/connect \
  -H "Content-Type: application/json" \
  -d '{"broker_name":"kraken","api_key":"xxx","api_secret":"yyy"}'

GET /api/brokers/status
Get status of all connected brokers
Response:
json{
  "brokers": [
    {
      "broker_id": "broker_kraken_001",
      "name": "Kraken",
      "status": "connected",
      "last_connection": "2024-06-13T14:32:00Z",
      "account_balance": 50000.00,
      "currency": "USD"
    },
    {
      "broker_id": "broker_ib_001",
      "name": "Interactive Brokers",
      "status": "connected",
      "last_connection": "2024-06-13T14:30:00Z",
      "account_balance": 100000.00,
      "currency": "USD"
    }
  ]
}

GET /api/brokers/{broker}/accounts
List accounts for specific broker
Parameters:

broker (path): Broker name (kraken, interactive_brokers, coinbase)

Response:
json{
  "broker": "kraken",
  "accounts": [
    {
      "account_id": "default",
      "balance": 50000.00,
      "currency": "USD",
      "is_paper_trading": false
    }
  ]
}

GET /api/brokers/{broker}/test-connection
Test broker connection
Parameters:

broker (path): Broker name

Response (Success):
json{
  "broker": "kraken",
  "status": "connected",
  "message": "Successfully connected to Kraken",
  "account_balance": 50000.00
}
Response (Error):
json{
  "broker": "kraken",
  "status": "error",
  "message": "Invalid API key or network error"
}

Trade Endpoints (/api/trades)
GET /api/trades
Get trade history (all agents)
Parameters:

page (optional): Page number (default: 1)
limit (optional): Results per page (default: 50, max: 100)
agent_id (optional): Filter by agent
symbol (optional): Filter by symbol
status (optional): Filter by status (open, closed, rejected)
start_date (optional): ISO format date
end_date (optional): ISO format date

Response:
json{
  "trades": [
    {
      "id": "trade_abc123",
      "agent_id": "agent_abc123",
      "agent_name": "BTC Momentum Trader",
      "symbol": "BTC/USD",
      "side": "BUY",
      "quantity": 0.05,
      "entry_price": 45230.50,
      "entry_time": "2024-06-13T10:15:00Z",
      "exit_price": 46100.00,
      "exit_time": "2024-06-13T11:30:00Z",
      "p_and_l": 435.25,
      "p_and_l_percent": 1.92,
      "reason": "Price broke above 20-day MA",
      "status": "closed"
    }
  ],
  "total": 847,
  "pages": 17
}

GET /api/trades/{id}
Get specific trade details
Parameters:

id (path): Trade ID

Response:
json{
  "id": "trade_abc123",
  "agent_id": "agent_abc123",
  "agent_name": "BTC Momentum Trader",
  "symbol": "BTC/USD",
  "broker": "kraken",
  "side": "BUY",
  "quantity": 0.05,
  "entry_price": 45230.50,
  "entry_time": "2024-06-13T10:15:00Z",
  "exit_price": 46100.00,
  "exit_time": "2024-06-13T11:30:00Z",
  "p_and_l": 435.25,
  "p_and_l_percent": 1.92,
  "reason": "Price broke above 20-day MA, RSI < 70, volume spike detected",
  "status": "closed",
  "order_id": "order_12345",
  "execution_mode": "human_in_loop",
  "confidence_score": 0.78,
  "market_data_snapshot": {
    "price": 45230.50,
    "rsi": 62.5,
    "volume": 2500000
  }
}

POST /api/trades/export
Export trades as CSV or PDF
Request Body:
json{
  "format": "csv",
  "start_date": "2024-01-01",
  "end_date": "2024-06-30",
  "agent_ids": ["agent_abc123", "agent_xyz789"],
  "include_fields": ["date", "agent", "symbol", "side", "quantity", "p_and_l", "reason"]
}
Response:
json{
  "status": "exported",
  "file_url": "/api/files/export_2024-06-13.csv",
  "filename": "trades_2024-01-01_to_2024-06-30.csv",
  "record_count": 847
}

Dashboard Endpoints (/api/dashboard)
GET /api/dashboard/summary
Portfolio overview
Response:
json{
  "total_balance": 112340.00,
  "cash": 8500.00,
  "invested": 103840.00,
  "p_and_l": 12340.00,
  "p_and_l_percent": 12.3,
  "return_30d": 4.2,
  "return_ytd": 18.5,
  "max_drawdown": -8.3,
  "sharpe_ratio": 1.4,
  "num_agents_active": 9,
  "num_agents_paused": 2,
  "last_trade": "2024-06-13T14:32:00Z"
}

GET /api/dashboard/performance
Agent leaderboard
Parameters:

sort_by (optional): return, sharpe, win_rate (default: return)
limit (optional): Number of results (default: 10)
order (optional): asc, desc (default: desc)

Response:
json{
  "agents": [
    {
      "id": "agent_abc123",
      "name": "Stock Picker",
      "room": "long_term",
      "return_percent": 13.3,
      "sharpe_ratio": 1.8,
      "win_rate": 0.75,
      "num_trades": 12,
      "max_drawdown": -5.2,
      "status": "active",
      "confidence_score": 88
    }
  ]
}

GET /api/dashboard/allocation
Capital allocation by room
Response:
json{
  "day_trading": {
    "allocated_percent": 10,
    "current_percent": 9.8,
    "allocated_amount": 10000,
    "current_amount": 9800,
    "num_agents": 3,
    "p_and_l": 250
  },
  "swing_trading": {
    "allocated_percent": 30,
    "current_percent": 31.2,
    "allocated_amount": 30000,
    "current_amount": 31200,
    "num_agents": 2,
    "p_and_l": 5200
  },
  "long_term_investment": {
    "allocated_percent": 60,
    "current_percent": 58.9,
    "allocated_amount": 60000,
    "current_amount": 59040,
    "num_agents": 2,
    "p_and_l": 5040
  }
}

GET /api/dashboard/equity-curve
Portfolio equity over time
Parameters:

timeframe (optional): 1d, 1w, 1m, 3m, 6m, 1y, all (default: 1m)

Response:
json{
  "timeframe": "1m",
  "data_points": 30,
  "equity": [
    {
      "timestamp": "2024-05-14T00:00:00Z",
      "balance": 100000.00,
      "p_and_l": 0.00,
      "p_and_l_percent": 0.0
    },
    {
      "timestamp": "2024-05-15T00:00:00Z",
      "balance": 102100.00,
      "p_and_l": 2100.00,
      "p_and_l_percent": 2.1
    }
  ]
}

Settings Endpoints (/api/settings)
POST /api/settings/allocation
Update capital allocation between rooms
Request Body:
json{
  "day_trading_percent": 5,
  "swing_trading_percent": 25,
  "long_term_percent": 70
}
Response:
json{
  "status": "updated",
  "allocation": {
    "day_trading": 5,
    "swing_trading": 25,
    "long_term": 70
  },
  "message": "Capital allocation updated. Rebalancing in progress..."
}

POST /api/settings/llm
Configure LLM (local or cloud)
Request Body (Local):
json{
  "use_local_llm": true,
  "ollama_model": "mistral"
}
Request Body (Cloud):
json{
  "use_local_llm": false,
  "provider": "anthropic",
  "api_key": "sk-ant-...",
  "model": "claude-sonnet-4-20250514"
}
Response:
json{
  "status": "configured",
  "llm_provider": "local_ollama",
  "model": "mistral",
  "message": "LLM configuration updated successfully"
}

POST /api/settings/vault-password
Change vault password
Request Body:
json{
  "old_password": "OldPassword#123",
  "new_password": "NewPassword#456"
}
Response:
json{
  "status": "password_changed",
  "message": "Vault password updated successfully"
}

GET /api/settings
Get all settings
Response:
json{
  "llm_config": {
    "use_local_llm": true,
    "provider": "ollama",
    "model": "mistral"
  },
  "brokers": [
    {
      "id": "broker_kraken_001",
      "name": "Kraken",
      "status": "connected"
    }
  ],
  "allocation": {
    "day_trading": 10,
    "swing_trading": 30,
    "long_term": 60
  },
  "risk_limits": {
    "max_portfolio_drawdown": -20,
    "max_position_size": 0.07,
    "max_sector_exposure": 0.25
  },
  "execution_modes": {
    "day_trading_default": "human_in_loop",
    "swing_trading_default": "human_in_loop",
    "long_term_default": "autonomous"
  }
}

Health Check Endpoint
GET /api/health
System health check
Response:
json{
  "status": "healthy",
  "uptime_seconds": 3600,
  "version": "1.0.0",
  "agents_active": 9,
  "brokers_connected": 2,
  "database": "healthy",
  "llm": "healthy",
  "timestamp": "2024-06-13T14:32:00Z"
}

WebSocket Endpoint (/ws)
Connect: ws://localhost:8000/ws
Messages from Server
Trade Executed
json{
  "type": "trade_executed",
  "agent_id": "agent_abc123",
  "trade": {
    "id": "trade_xyz789",
    "symbol": "BTC/USD",
    "side": "BUY",
    "quantity": 0.05,
    "entry_price": 45230.50,
    "p_and_l": 435.25
  },
  "timestamp": "2024-06-13T10:15:00Z"
}
Trade Approval Needed
json{
  "type": "agent_approval_needed",
  "agent_id": "agent_abc123",
  "agent_name": "BTC Momentum Trader",
  "trade": {
    "id": "trade_xyz789",
    "symbol": "BTC/USD",
    "side": "BUY",
    "quantity": 0.05,
    "entry_price": 45230.50,
    "confidence": 0.78,
    "reason": "Price broke above 20-day MA"
  },
  "timeout_seconds": 30,
  "timestamp": "2024-06-13T10:15:00Z"
}
Agent Paused
json{
  "type": "agent_paused",
  "agent_id": "agent_abc123",
  "agent_name": "Tech Trader",
  "reason": "losing_streak",
  "details": "5 consecutive losses detected",
  "timestamp": "2024-06-13T14:00:00Z"
}
P&L Update
json{
  "type": "p_and_l_update",
  "total_balance": 112340.00,
  "total_p_and_l": 12340.00,
  "total_p_and_l_percent": 12.3,
  "by_room": {
    "day_trading": 250,
    "swing_trading": 5200,
    "long_term": 5040
  },
  "timestamp": "2024-06-13T14:32:00Z"
}
Messages to Server
Approve Trade
json{
  "type": "approve_trade",
  "agent_id": "agent_abc123",
  "trade_id": "trade_xyz789",
  "approved": true
}
Request Update
json{
  "type": "request_update",
  "requested_data": "dashboard_summary"
}

Common cURL Examples
Create an Agent
bashcurl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Energy Sector Trader",
    "room": "sector_trading",
    "asset": "XLE",
    "broker": "kraken",
    "context_file_content": "AGENT NAME: Energy Trader\nROOM: sector_trading..."
  }'
Get Agent Details
bashcurl http://localhost:8000/api/agents/agent_abc123
Approve a Trade
bashcurl -X POST http://localhost:8000/api/agents/agent_abc123/approve \
  -H "Content-Type: application/json" \
  -d '{
    "trade_id": "trade_xyz789",
    "approved": true
  }'
Get Portfolio Summary
bashcurl http://localhost:8000/api/dashboard/summary
Export Trades
bashcurl -X POST http://localhost:8000/api/trades/export \
  -H "Content-Type: application/json" \
  -d '{
    "format": "csv",
    "start_date": "2024-01-01",
    "end_date": "2024-06-30"
  }'
Test Broker Connection
bashcurl http://localhost:8000/api/brokers/kraken/test-connection

Rate Limiting
Local machine only: No rate limits applied.
If using cloud LLM (Claude/GPT), those APIs have their own rate limits:

Claude API: 5 requests/minute on free tier
GPT-4 API: 3 requests/minute on free tier

Labourious respects these limits and queues requests accordingly.

Authentication
All endpoints are unauthenticated (local machine only).
For remote access (future mobile apps), authentication will be added.

Versioning
Current API version: v1.0.0 (MVP)
API endpoints follow this convention:

/api/* - v1.0 endpoints (current)
Future: /api/v2/* - v2.0 endpoints (backward compatible)


Deprecation Policy
Endpoints marked as [DEPRECATED] in future versions will:

Continue to work for 2 major versions
Display deprecation warnings in logs
Be fully replaced in the next major version


Testing API Locally
Using Postman

Import this API reference
Set base URL: http://localhost:8000
Test endpoints directly

Using cURL
See "Common cURL Examples" section above.
Using Python
pythonimport requests

response = requests.get('http://localhost:8000/api/agents')
agents = response.json()
print(agents)
Using JavaScript
javascriptfetch('http://localhost:8000/api/agents')
  .then(r => r.json())
  .then(data => console.log(data));

WebSocket Testing
Using wscat or similar tool:
bashnpm install -g wscat
wscat -c ws://localhost:8000/ws

# Then send messages like:
{"type": "request_update", "requested_data": "dashboard_summary"}

Troubleshooting
Connection Refused

Ensure backend is running: python main.py
Check port 8000 is not blocked by firewall
Verify no other app is using port 8000

Invalid JSON

Ensure request body is valid JSON
Check Content-Type header is application/json
Use a JSON validator

Agent Not Found

Verify agent ID is correct (copy from /api/agents)
Check agent hasn't been deleted
Check spelling and case-sensitivity

Broker Connection Error

Verify broker credentials are correct
Check broker API is enabled on account
Test connection using /api/brokers/{broker}/test-connection


For more help, see TROUBLESHOOTING.md or open an issue on GitHub.
