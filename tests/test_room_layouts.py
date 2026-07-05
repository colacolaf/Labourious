import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

from backend.main import app
from backend.database.models import Base, Agent, AgentStatus, User, UserRole

_test_engine = None
_test_session_factory = None


def setup_test_db():
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
    setup_test_db()
    yield


@pytest.fixture
def client():
    session = _test_session_factory()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()

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

    import backend.api.room_layouts as room_layouts_module
    import backend.api.agent_appearance as agent_appearance_module
    originals = (room_layouts_module.get_db_session, agent_appearance_module.get_db_session)
    room_layouts_module.get_db_session = override_get_db_session
    agent_appearance_module.get_db_session = override_get_db_session

    import backend.api.agents as agents_module
    original_agents_get_db_session = agents_module.get_db_session
    agents_module.get_db_session = override_get_db_session

    from backend.auth.dependencies import get_current_user
    user_session = _test_session_factory()
    user_session.add(User(id="test-user", username="testuser", email="u@u.com",
                           hashed_password="x", role=UserRole.ADMIN))
    user_session.commit()
    user_session.close()
    # Fresh, never-session-tracked object (mirrors test_api_agents.py) — the persisted row
    # above is what endpoints re-query; this object is only used to satisfy the dependency.
    _user = User(id="test-user", username="testuser", email="u@u.com",
                 hashed_password="x", role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: _user

    client = TestClient(app)
    yield client

    room_layouts_module.get_db_session, agent_appearance_module.get_db_session = originals
    agents_module.get_db_session = original_agents_get_db_session
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def agent_factory():
    import time
    counter = [0]

    def create_agent(**kwargs):
        session = _test_session_factory()
        try:
            defaults = {
                "name": f"agent_{counter[0]}_{int(time.time()*1000000)}",
                "symbol": "BTC/USD",
                "status": AgentStatus.IDLE,
                "is_active": True,
            }
            defaults.update(kwargs)
            agent = Agent(**defaults)
            session.add(agent)
            session.flush()
            agent_id = agent.id
            session.commit()
            counter[0] += 1

            class AgentRef:
                def __init__(self, id):
                    self.id = id

            return AgentRef(agent_id)
        finally:
            session.close()

    return create_agent


class TestRoomLayouts:
    def test_get_room_layout_no_custom(self, client):
        resp = client.get("/api/room-layouts/long_term")
        assert resp.status_code == 200
        assert resp.json() == {"custom": False}

    def test_save_and_get_room_layout(self, client):
        map_json = {"name": "custom", "layers": {"floor": [], "walls": []}}
        resp = client.put("/api/room-layouts/long_term", json={"map_json": map_json})
        assert resp.status_code == 200
        assert resp.json()["map_json"] == map_json

        resp = client.get("/api/room-layouts/long_term")
        assert resp.status_code == 200
        data = resp.json()
        assert data["custom"] is True
        assert data["map_json"] == map_json

    def test_save_overwrites_existing(self, client):
        client.put("/api/room-layouts/day_trading", json={"map_json": {"v": 1}})
        resp = client.put("/api/room-layouts/day_trading", json={"map_json": {"v": 2}})
        assert resp.status_code == 200
        assert resp.json()["map_json"] == {"v": 2}

    def test_reset_room_layout(self, client):
        client.put("/api/room-layouts/swing_trading", json={"map_json": {"v": 1}})
        resp = client.delete("/api/room-layouts/swing_trading")
        assert resp.status_code == 204

        resp = client.get("/api/room-layouts/swing_trading")
        assert resp.json() == {"custom": False}

    def test_reset_room_layout_missing_is_noop(self, client):
        resp = client.delete("/api/room-layouts/long_term")
        assert resp.status_code == 204


class TestAgentAppearance:
    def test_get_appearance_agent_not_found(self, client):
        resp = client.get("/api/agents/9999/appearance")
        assert resp.status_code == 404

    def test_get_appearance_null_by_default(self, client, agent_factory):
        agent = agent_factory(name="appearance_default")
        resp = client.get(f"/api/agents/{agent.id}/appearance")
        assert resp.status_code == 200
        assert resp.json() == {"appearance": None}

    def test_save_and_get_appearance(self, client, agent_factory):
        agent = agent_factory(name="appearance_save")
        appearance = {"bodyType": "male", "layers": {"body": {"itemKey": "body", "variant": "light"}}}
        resp = client.put(f"/api/agents/{agent.id}/appearance", json={"appearance": appearance})
        assert resp.status_code == 200
        assert resp.json()["appearance"] == appearance

        resp = client.get(f"/api/agents/{agent.id}/appearance")
        assert resp.json()["appearance"] == appearance

    def test_save_appearance_agent_not_found(self, client):
        resp = client.put("/api/agents/9999/appearance", json={"appearance": {"bodyType": "male", "layers": {}}})
        assert resp.status_code == 404

    def test_agent_list_response_includes_appearance(self, client, agent_factory):
        agent = agent_factory(name="appearance_in_list")
        appearance = {"bodyType": "female", "layers": {}}
        client.put(f"/api/agents/{agent.id}/appearance", json={"appearance": appearance})

        resp = client.get("/api/agents")
        data = resp.json()
        assert data[0]["appearance"] == appearance


class TestUserAvatarAppearance:
    def test_get_user_avatar_default(self, client):
        resp = client.get("/api/user/avatar-appearance")
        assert resp.status_code == 200
        assert resp.json() == {"appearance": None}

    def test_save_and_get_user_avatar(self, client):
        appearance = {"bodyType": "male", "layers": {}}
        resp = client.put("/api/user/avatar-appearance", json={"appearance": appearance})
        assert resp.status_code == 200
        assert resp.json()["appearance"] == appearance

        resp = client.get("/api/user/avatar-appearance")
        assert resp.json()["appearance"] == appearance
