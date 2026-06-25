import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import tempfile
import os

from backend.main import app
from backend.database.models import Base, Agent, AgentStatus, Trade, TradeSide, TradeStatus, Performance, User, UserRole
from backend.config import settings

# Global test database and session factory
_test_engine = None
_test_session_factory = None


def setup_test_db():
    """Setup test database."""
    global _test_engine, _test_session_factory
    _test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=_test_engine)
    _test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_fixtures():
    """Setup test fixtures once per session."""
    setup_test_db()
    yield


@pytest.fixture
def client():
    """Create a test client with in-memory DB."""
    # Clear all tables before each test
    session = _test_session_factory()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()

    # Override get_db_session to use test database
    def override_get_db_session(database_url):
        @contextmanager
        def session_maker():
            session = _test_session_factory()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        return session_maker()

    # Patch the get_db_session function in agents module
    import backend.api.agents as agents_module
    original_get_db_session = agents_module.get_db_session
    agents_module.get_db_session = override_get_db_session

    # Override auth so legacy tests don't need tokens — inject admin user
    from backend.auth.dependencies import get_current_user
    _admin = User(id="test-admin", username="testadmin", email="a@a.com",
                  hashed_password="x", role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: _admin

    client = TestClient(app)
    yield client

    # Restore originals
    agents_module.get_db_session = original_get_db_session
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def agent_factory():
    """Factory to create agents in test DB."""
    import time
    counter = [0]

    def create_agent(**kwargs):
        session = _test_session_factory()
        try:
            # Use counter + timestamp to ensure uniqueness
            defaults = {
                "name": f"agent_{counter[0]}_{int(time.time()*1000000)}",
                "symbol": "BTC/USD",
                "exchange": "binance",
                "timeframe": "1h",
                "status": AgentStatus.IDLE,
                "is_active": True,
            }
            defaults.update(kwargs)
            agent = Agent(**defaults)
            session.add(agent)
            session.flush()
            # Get the ID before closing session
            agent_id = agent.id
            session.commit()
            counter[0] += 1

            # Return a simple dict-like object with just the ID (not a detached ORM object)
            class AgentRef:
                def __init__(self, id):
                    self.id = id

            return AgentRef(agent_id)
        finally:
            session.close()

    return create_agent


class TestListAgents:
    def test_list_agents_empty(self, client):
        """GET /api/agents returns 200 with empty list."""
        response = client.get("/api/agents")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_agents_with_data(self, client, agent_factory):
        """GET /api/agents returns agents."""
        agent = agent_factory(name="test_agent", symbol="ETH/USD")
        response = client.get("/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test_agent"
        assert data[0]["symbol"] == "ETH/USD"

    def test_list_agents_filter_by_room(self, client, agent_factory):
        """GET /api/agents?room=x filters by room."""
        agent_factory(name="agent1", room="day_trading")
        agent_factory(name="agent2", room="swing_trading")
        response = client.get("/api/agents?room=day_trading")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["room"] == "day_trading"

    def test_list_agents_filter_by_is_active(self, client, agent_factory):
        """GET /api/agents?is_active=true filters by active status."""
        agent_factory(name="active_agent", is_active=True)
        agent_factory(name="inactive_agent", is_active=False)
        response = client.get("/api/agents?is_active=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_active"] is True


class TestCreateAgent:
    def test_create_agent_minimal(self, client):
        """POST /api/agents with name+symbol returns 201 with agent."""
        payload = {"name": "test_agent", "symbol": "BTC/USD"}
        response = client.post("/api/agents", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "test_agent"
        assert data["symbol"] == "BTC/USD"
        assert data["exchange"] == "binance"
        assert data["is_active"] is True

    def test_create_agent_full(self, client):
        """POST /api/agents with all fields."""
        payload = {
            "name": "full_agent",
            "symbol": "ETH/USD",
            "exchange": "kraken",
            "timeframe": "15m",
            "is_paper_trading": False,
            "is_active": False,
            "room": "scalping",
            "broker": "interactive_brokers",
            "max_position_size": 5000.0,
            "stop_loss_pct": 1.5,
            "take_profit_pct": 3.0,
        }
        response = client.post("/api/agents", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "full_agent"
        assert data["exchange"] == "kraken"
        assert data["room"] == "scalping"
        assert data["max_position_size"] == 5000.0

    def test_create_agent_missing_name(self, client):
        """POST /api/agents without name returns 422."""
        payload = {"symbol": "BTC/USD"}
        response = client.post("/api/agents", json=payload)
        assert response.status_code == 422


class TestGetAgent:
    def test_get_agent_success(self, client, agent_factory):
        """GET /api/agents/{id} returns agent."""
        agent = agent_factory(name="test_get")
        response = client.get(f"/api/agents/{agent.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == agent.id
        assert data["name"] == "test_get"

    def test_get_agent_not_found(self, client):
        """GET /api/agents/9999 returns 404."""
        response = client.get("/api/agents/9999")
        assert response.status_code == 404
        assert "Agent not found" in response.json()["detail"]


class TestUpdateAgent:
    def test_update_agent_partial(self, client, agent_factory):
        """PUT /api/agents/{id} updates fields."""
        agent = agent_factory(name="orig_agent")
        payload = {"name": "updated_agent", "exchange": "kraken"}
        response = client.put(f"/api/agents/{agent.id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated_agent"
        assert data["exchange"] == "kraken"
        assert data["symbol"] == "BTC/USD"  # unchanged

    def test_update_agent_not_found(self, client):
        """PUT /api/agents/9999 returns 404."""
        payload = {"name": "new_name"}
        response = client.put("/api/agents/9999", json=payload)
        assert response.status_code == 404


class TestDeleteAgent:
    def test_delete_agent_success(self, client, agent_factory):
        """DELETE /api/agents/{id} deletes agent."""
        agent = agent_factory(name="to_delete")
        response = client.delete(f"/api/agents/{agent.id}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/agents/{agent.id}")
        assert response.status_code == 404

    def test_delete_agent_not_found(self, client):
        """DELETE /api/agents/9999 returns 404."""
        response = client.delete("/api/agents/9999")
        assert response.status_code == 404


class TestToggleAgent:
    def test_toggle_agent_active_to_inactive(self, client, agent_factory):
        """POST /api/agents/{id}/toggle flips is_active."""
        agent = agent_factory(name="toggle_test", is_active=True)
        response = client.post(f"/api/agents/{agent.id}/toggle")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_toggle_agent_inactive_to_active(self, client, agent_factory):
        """POST /api/agents/{id}/toggle flips is_active back."""
        agent = agent_factory(name="toggle_test2", is_active=False)
        response = client.post(f"/api/agents/{agent.id}/toggle")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    def test_toggle_agent_not_found(self, client):
        """POST /api/agents/9999/toggle returns 404."""
        response = client.post("/api/agents/9999/toggle")
        assert response.status_code == 404


class TestResumeAgent:
    def test_resume_agent_resets_losses_and_status(self, client, agent_factory):
        """POST /api/agents/{id}/resume resets consecutive_losses and status."""
        agent = agent_factory(
            name="error_agent",
            status=AgentStatus.ERROR,
            consecutive_losses=5,
        )
        response = client.post(f"/api/agents/{agent.id}/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["consecutive_losses"] == 0
        assert data["status"] == "idle"

    def test_resume_agent_not_found(self, client):
        """POST /api/agents/9999/resume returns 404."""
        response = client.post("/api/agents/9999/resume")
        assert response.status_code == 404


class TestAgentTrades:
    def test_get_agent_trades_empty(self, client, agent_factory):
        """GET /api/agents/{id}/trades returns empty list."""
        agent = agent_factory(name="agent_no_trades")
        response = client.get(f"/api/agents/{agent.id}/trades")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_agent_trades_not_found(self, client):
        """GET /api/agents/9999/trades returns 404."""
        response = client.get("/api/agents/9999/trades")
        assert response.status_code == 404

    def test_get_agent_trades_with_data(self, client, agent_factory):
        """GET /api/agents/{id}/trades returns last 50 trades."""
        agent = agent_factory(name="agent_with_trades")

        # Add trades directly to DB
        session = _test_session_factory()
        try:
            for i in range(5):
                trade = Trade(
                    agent_id=agent.id,
                    symbol="BTC/USD",
                    side=TradeSide.BUY,
                    status=TradeStatus.CLOSED,
                    entry_price=50000.0 + i * 100,
                    exit_price=50500.0 + i * 100,
                    quantity=1.0,
                    pnl=500.0,
                )
                session.add(trade)
            session.commit()
        finally:
            session.close()

        response = client.get(f"/api/agents/{agent.id}/trades")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5


class TestAgentPerformance:
    def test_get_agent_performance_empty(self, client, agent_factory):
        """GET /api/agents/{id}/performance returns empty list."""
        agent = agent_factory(name="agent_no_perf")
        response = client.get(f"/api/agents/{agent.id}/performance")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_agent_performance_not_found(self, client):
        """GET /api/agents/9999/performance returns 404."""
        response = client.get("/api/agents/9999/performance")
        assert response.status_code == 404

    def test_get_agent_performance_with_data(self, client, agent_factory):
        """GET /api/agents/{id}/performance returns records."""
        agent = agent_factory(name="agent_with_perf")

        # Add performance records directly to DB
        session = _test_session_factory()
        try:
            for i in range(3):
                perf = Performance(
                    agent_id=agent.id,
                    period="daily",
                    portfolio_value=100000.0 + i * 1000,
                    cash_balance=50000.0,
                    total_pnl=1000.0 * i,
                    win_rate=0.6,
                )
                session.add(perf)
            session.commit()
        finally:
            session.close()

        response = client.get(f"/api/agents/{agent.id}/performance")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestAgentResponseFields:
    def test_agent_response_has_confidence_fields(self, client, agent_factory):
        """GET /api/agents returns confidence_score, execution_mode, check_frequency, paper_trading_balance, last_heartbeat."""
        agent_factory(name="test_confidence_agent")
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        assert len(agents) > 0
        a = agents[0]
        assert "confidence_score" in a
        assert "execution_mode" in a
        assert "check_frequency" in a
        assert "paper_trading_balance" in a
        assert "last_heartbeat" in a  # may be None


class TestEmergencyStop:
    def test_emergency_stop_pauses_all_active_agents(self, client, agent_factory):
        """POST /api/agents/emergency-stop sets all active agents to PAUSED and returns stopped count."""
        agent_factory(name="emergency_agent_1", symbol="BTC/USD", status=AgentStatus.RUNNING, is_active=True)
        agent_factory(name="emergency_agent_2", symbol="ETH/USD", status=AgentStatus.IDLE, is_active=True)
        resp = client.post("/api/agents/emergency-stop")
        assert resp.status_code == 200
        data = resp.json()
        assert "stopped" in data
        assert isinstance(data["stopped"], int)
        assert data["stopped"] == 2
        assert data["status"] == "all_agents_paused"

    def test_emergency_stop_returns_zero_when_no_agents(self, client):
        """POST /api/agents/emergency-stop returns stopped=0 when no active agents."""
        resp = client.post("/api/agents/emergency-stop")
        assert resp.status_code == 200
        assert resp.json()["stopped"] == 0


class TestVaultCheck:
    def test_vault_check_broker_returns_has_credentials(self, client):
        """GET /api/agents/brokers/vault-check/alpaca returns has_credentials field."""
        resp = client.get("/api/agents/brokers/vault-check/alpaca")
        assert resp.status_code == 200
        data = resp.json()
        assert "has_credentials" in data
        assert "broker" in data
        assert "required_keys" in data
