"""E2E smoke: register → login → agents → stop agent → token check."""
import pytest
import httpx
from httpx import ASGITransport
from backend.main import app
from backend.database.db import init_db
from backend.config import settings


BASE = "http://test"

TEST_USER = {"username": "smokeuser", "email": "smokeuser@example.com", "password": "SmokePass123!"}


@pytest.fixture(scope="module", autouse=True)
def _init_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("smoke") / "smoke.db"
    import backend.database.db as db_mod
    db_mod._engine = None
    db_mod._SessionLocal = None
    init_db(f"sqlite:///{db_path}")
    yield
    db_mod._engine = None
    db_mod._SessionLocal = None


@pytest.mark.asyncio
async def test_smoke_register_login_agents_stop():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        # Register
        r = await client.post("/api/auth/register", json=TEST_USER)
        assert r.status_code in (201, 409), f"register: {r.text}"

        # Login
        r = await client.post("/api/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"],
        })
        assert r.status_code == 200, f"login: {r.text}"
        tokens = r.json()
        assert "access_token" in tokens
        access = tokens["access_token"]
        headers = {"Authorization": f"Bearer {access}"}

        # Get agents (may be empty list)
        r = await client.get("/api/agents", headers=headers)
        assert r.status_code == 200, f"agents: {r.text}"
        agents = r.json()
        assert isinstance(agents, (list, dict))

        # If agents exist, stop first one
        agent_list = agents if isinstance(agents, list) else agents.get("items", [])
        if agent_list:
            agent_id = agent_list[0]["id"]
            r = await client.post(f"/api/agents/{agent_id}/stop", headers=headers)
            assert r.status_code in (200, 404, 422), f"stop: {r.text}"

        # Verify token still valid via /me
        r = await client.get("/api/auth/me", headers=headers)
        assert r.status_code == 200, f"me: {r.text}"

        # Invalid token → 401 or 403
        r = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token"})
        assert r.status_code in (401, 403), f"invalid token check: {r.text}"
