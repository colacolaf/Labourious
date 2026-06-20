"""4A.11: Full auth integration — register → login → CRUD agents → logout."""
import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

from backend.main import app
from backend.database.models import Base
from backend.config import settings

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_engine)
_Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture
def client():
    session = _Session()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()

    def override_get_db_session(url):
        @contextmanager
        def maker():
            s = _Session()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()
        return maker()

    import backend.api.agents as agents_module
    import backend.auth.dependencies as deps_module
    orig_session = agents_module.get_db_session
    orig_factory = deps_module.get_session_factory
    agents_module.get_db_session = override_get_db_session
    deps_module.get_session_factory = lambda url: _Session

    # Clear any leftover dependency overrides from other test modules
    app.dependency_overrides.clear()

    yield TestClient(app)

    agents_module.get_db_session = orig_session
    deps_module.get_session_factory = orig_factory
    app.dependency_overrides.clear()


def test_full_auth_flow(client):
    """register → login → create agent → list (owner-scoped) → delete → verify gone."""
    n = int(time.time() * 1e6)

    # Register
    r = client.post("/api/auth/register", json={
        "username": f"trader_{n}",
        "email": f"trader_{n}@test.com",
        "password": "SecurePass123!",
    })
    assert r.status_code == 201, r.text
    user_id = r.json()["id"]

    # Login
    r = client.post("/api/auth/login", json={
        "email": f"trader_{n}@test.com",
        "password": "SecurePass123!",
    })
    assert r.status_code == 200, r.text
    tokens = r.json()
    assert "access_token" in tokens
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # GET /me
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == user_id

    # Create agent
    r = client.post("/api/agents", json={"name": f"mybot_{n}", "symbol": "BTC/USD"}, headers=headers)
    assert r.status_code == 201, r.text
    agent_id = r.json()["id"]

    # List — should see own agent
    r = client.get("/api/agents", headers=headers)
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert agent_id in ids

    # Refresh token
    r = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    new_token = r.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}

    # Delete with new token
    r = client.delete(f"/api/agents/{agent_id}", headers=new_headers)
    assert r.status_code == 204

    # Verify gone
    r = client.get(f"/api/agents/{agent_id}", headers=new_headers)
    assert r.status_code == 404


def test_cross_user_isolation(client):
    """Two traders cannot see each other's agents."""
    n = int(time.time() * 1e6)

    def register_and_login(suffix):
        client.post("/api/auth/register", json={
            "username": f"usr_{n}_{suffix}",
            "email": f"usr_{n}_{suffix}@t.com",
            "password": "SecurePass123!",
        })
        r = client.post("/api/auth/login", json={
            "email": f"usr_{n}_{suffix}@t.com",
            "password": "SecurePass123!",
        })
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    h1 = register_and_login("a")
    h2 = register_and_login("b")

    # Alice creates agent
    r = client.post("/api/agents", json={"name": f"alice_bot_{n}", "symbol": "ETH/USD"}, headers=h1)
    assert r.status_code == 201
    alice_agent_id = r.json()["id"]

    # Bob cannot see Alice's agent in list
    r = client.get("/api/agents", headers=h2)
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert alice_agent_id not in ids

    # Bob cannot get Alice's agent directly
    r = client.get(f"/api/agents/{alice_agent_id}", headers=h2)
    assert r.status_code == 403
