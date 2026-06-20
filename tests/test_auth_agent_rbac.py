"""4A.5-4A.9: Agent endpoint RBAC tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

from backend.main import app
from backend.database.models import Base, Agent, User, UserRole, AgentStatus
from backend.auth.utils import hash_password, create_access_token
from backend.config import settings

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_engine)
_Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def clear_db():
    session = _Session()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()


@pytest.fixture
def client():
    def override_get_db_session(database_url):
        @contextmanager
        def session_maker():
            session = _Session()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        return session_maker()

    import backend.api.agents as agents_module
    orig = agents_module.get_db_session
    agents_module.get_db_session = override_get_db_session

    # Auth dependencies use get_session_factory — override it too
    import backend.auth.dependencies as deps_module
    orig_factory = deps_module.get_session_factory
    deps_module.get_session_factory = lambda url: _Session

    yield TestClient(app)

    agents_module.get_db_session = orig
    deps_module.get_session_factory = orig_factory


_user_counter = [0]

def _make_user(session, role=UserRole.TRADER):
    _user_counter[0] += 1
    n = _user_counter[0]
    uid = f"u{n}"
    user = User(
        id=uid,
        username=f"user_{n}",
        email=f"user_{n}@example.com",
        hashed_password=hash_password("pass1234"),
        role=role,
    )
    session.add(user)
    session.commit()
    return user


def _make_agent(session, user_id, name_suffix=""):
    import time
    agent = Agent(
        user_id=user_id,
        name=f"agent_{user_id[:6]}_{name_suffix}_{int(time.time()*1e6)}",
        symbol="BTC/USD",
        exchange="binance",
        timeframe="1h",
        status=AgentStatus.IDLE,
    )
    session.add(agent)
    session.commit()
    return agent


def _token(user_id):
    return {"Authorization": f"Bearer {create_access_token({'sub': user_id})}"}


# --- 4A.5: Auth required ---

class TestAuthRequired:
    def test_list_no_token_returns_401_or_403(self, client):
        assert client.get("/api/agents").status_code in (401, 403)

    def test_create_no_token_returns_401_or_403(self, client):
        assert client.post("/api/agents", json={"name": "x", "symbol": "BTC/USD"}).status_code in (401, 403)

    def test_get_no_token_returns_401_or_403(self, client):
        assert client.get("/api/agents/1").status_code in (401, 403)

    def test_delete_no_token_returns_401_or_403(self, client):
        assert client.delete("/api/agents/1").status_code in (401, 403)


# --- 4A.6: Ownership scoping ---

class TestOwnershipScoping:
    def test_trader_sees_only_own_agents(self, client):
        session = _Session()
        try:
            alice = _make_user(session, UserRole.TRADER)
            bob = _make_user(session, UserRole.TRADER)
            _make_agent(session, alice.id, "a")
            _make_agent(session, bob.id, "b")
            alice_id = alice.id
            bob_id = bob.id
        finally:
            session.close()

        resp = client.get("/api/agents", headers=_token(alice_id))
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.json()]
        # Alice's agent returns, Bob's does not
        assert len(ids) == 1

    def test_admin_sees_all_agents(self, client):
        session = _Session()
        try:
            alice = _make_user(session, UserRole.TRADER)
            admin = _make_user(session, UserRole.ADMIN)
            _make_agent(session, alice.id, "a")
            _make_agent(session, admin.id, "b")
            admin_id = admin.id
        finally:
            session.close()

        resp = client.get("/api/agents", headers=_token(admin_id))
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_create_assigns_user_id(self, client):
        session = _Session()
        try:
            alice = _make_user(session, UserRole.TRADER)
            alice_id = alice.id
        finally:
            session.close()

        import time
        resp = client.post(
            "/api/agents",
            json={"name": f"myagent_{int(time.time()*1e6)}", "symbol": "ETH/USD"},
            headers=_token(alice_id),
        )
        assert resp.status_code == 201
        agent_id = resp.json()["id"]

        session = _Session()
        try:
            agent = session.query(Agent).filter_by(id=agent_id).first()
            assert agent.user_id == alice_id
        finally:
            session.close()


# --- 4A.7-4A.9: Cross-user access denied ---

class TestCrossUserAccess:
    def test_trader_cannot_get_other_user_agent(self, client):
        session = _Session()
        try:
            alice = _make_user(session, UserRole.TRADER)
            bob = _make_user(session, UserRole.TRADER)
            agent = _make_agent(session, bob.id, "b")
            alice_id = alice.id
            agent_id = agent.id
        finally:
            session.close()

        resp = client.get(f"/api/agents/{agent_id}", headers=_token(alice_id))
        assert resp.status_code == 403

    def test_trader_cannot_delete_other_user_agent(self, client):
        session = _Session()
        try:
            alice = _make_user(session, UserRole.TRADER)
            bob = _make_user(session, UserRole.TRADER)
            agent = _make_agent(session, bob.id, "b")
            alice_id = alice.id
            agent_id = agent.id
        finally:
            session.close()

        resp = client.delete(f"/api/agents/{agent_id}", headers=_token(alice_id))
        assert resp.status_code == 403

    def test_trader_cannot_update_other_user_agent(self, client):
        session = _Session()
        try:
            alice = _make_user(session, UserRole.TRADER)
            bob = _make_user(session, UserRole.TRADER)
            agent = _make_agent(session, bob.id, "b")
            alice_id = alice.id
            agent_id = agent.id
        finally:
            session.close()

        resp = client.put(
            f"/api/agents/{agent_id}",
            json={"symbol": "ETH/USD"},
            headers=_token(alice_id),
        )
        assert resp.status_code == 403

    def test_admin_can_get_any_agent(self, client):
        session = _Session()
        try:
            bob = _make_user(session, UserRole.TRADER)
            admin = _make_user(session, UserRole.ADMIN)
            agent = _make_agent(session, bob.id, "b")
            admin_id = admin.id
            agent_id = agent.id
        finally:
            session.close()

        resp = client.get(f"/api/agents/{agent_id}", headers=_token(admin_id))
        assert resp.status_code == 200

    def test_admin_can_delete_any_agent(self, client):
        session = _Session()
        try:
            bob = _make_user(session, UserRole.TRADER)
            admin = _make_user(session, UserRole.ADMIN)
            agent = _make_agent(session, bob.id, "b")
            admin_id = admin.id
            agent_id = agent.id
        finally:
            session.close()

        resp = client.delete(f"/api/agents/{agent_id}", headers=_token(admin_id))
        assert resp.status_code == 204
