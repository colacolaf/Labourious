"""4B.4: Notifications preferences endpoints tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

from backend.main import app
from backend.database.models import Base, User, UserRole
from backend.notifications.models import UserNotificationPreferences
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
    # Override get_session_factory to use in-memory DB
    import backend.auth.dependencies as deps_module
    orig_factory = deps_module.get_session_factory
    deps_module.get_session_factory = lambda url: _Session

    yield TestClient(app)

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


def _token(user_id):
    return {"Authorization": f"Bearer {create_access_token({'sub': user_id})}"}


class TestGetPreferences:
    def test_get_preferences_creates_default_if_none_exist(self, client):
        """GET /api/notifications/preferences creates default prefs if none exist."""
        session = _Session()
        try:
            user = _make_user(session)
            headers = _token(user.id)

            response = client.get("/api/notifications/preferences", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["email_enabled"] is True
            assert data["sms_enabled"] is False
            assert data["phone_number"] is None
            assert data["notify_on_trade"] is True
            assert data["notify_on_agent_pause"] is True
            assert data["notify_on_drawdown"] is True
            assert data["daily_digest"] is False
        finally:
            session.close()

    def test_get_preferences_returns_existing_preferences(self, client):
        """GET /api/notifications/preferences returns existing preferences."""
        session = _Session()
        try:
            user = _make_user(session)
            prefs = UserNotificationPreferences(
                user_id=user.id,
                email_enabled=False,
                sms_enabled=True,
                phone_number="+1234567890",
                notify_on_trade=False,
                notify_on_agent_pause=False,
                notify_on_drawdown=True,
                daily_digest=True,
            )
            session.add(prefs)
            session.commit()

            headers = _token(user.id)
            response = client.get("/api/notifications/preferences", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["email_enabled"] is False
            assert data["sms_enabled"] is True
            assert data["phone_number"] == "+1234567890"
            assert data["notify_on_trade"] is False
            assert data["notify_on_agent_pause"] is False
            assert data["notify_on_drawdown"] is True
            assert data["daily_digest"] is True
        finally:
            session.close()

    def test_get_preferences_without_token_returns_401_or_403(self, client):
        """GET /api/notifications/preferences without token returns 401 or 403."""
        response = client.get("/api/notifications/preferences")
        assert response.status_code in (401, 403)


class TestPatchPreferences:
    def test_patch_preferences_updates_only_supplied_fields(self, client):
        """PATCH /api/notifications/preferences updates only supplied fields."""
        session = _Session()
        try:
            user = _make_user(session)
            prefs = UserNotificationPreferences(
                user_id=user.id,
                email_enabled=True,
                sms_enabled=False,
                phone_number=None,
                notify_on_trade=True,
                notify_on_agent_pause=True,
                notify_on_drawdown=True,
                daily_digest=False,
            )
            session.add(prefs)
            session.commit()

            headers = _token(user.id)
            response = client.patch(
                "/api/notifications/preferences",
                headers=headers,
                json={"email_enabled": False, "sms_enabled": True}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_enabled"] is False
            assert data["sms_enabled"] is True
            # Other fields unchanged
            assert data["phone_number"] is None
            assert data["notify_on_trade"] is True
            assert data["notify_on_agent_pause"] is True
            assert data["notify_on_drawdown"] is True
            assert data["daily_digest"] is False
        finally:
            session.close()

    def test_patch_preferences_with_empty_body_changes_nothing(self, client):
        """PATCH /api/notifications/preferences with empty body changes nothing."""
        session = _Session()
        try:
            user = _make_user(session)
            prefs = UserNotificationPreferences(
                user_id=user.id,
                email_enabled=False,
                sms_enabled=True,
                phone_number="+1234567890",
            )
            session.add(prefs)
            session.commit()

            headers = _token(user.id)
            response = client.patch(
                "/api/notifications/preferences",
                headers=headers,
                json={}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_enabled"] is False
            assert data["sms_enabled"] is True
            assert data["phone_number"] == "+1234567890"
        finally:
            session.close()

    def test_patch_preferences_creates_default_if_none_exist(self, client):
        """PATCH /api/notifications/preferences creates default prefs if none exist."""
        session = _Session()
        try:
            user = _make_user(session)
            headers = _token(user.id)

            response = client.patch(
                "/api/notifications/preferences",
                headers=headers,
                json={"email_enabled": False}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_enabled"] is False
            # Other fields have defaults
            assert data["sms_enabled"] is False
            assert data["notify_on_trade"] is True
        finally:
            session.close()

    def test_patch_preferences_clears_phone_number_with_null(self, client):
        """PATCH /api/notifications/preferences with phone_number: null clears it."""
        session = _Session()
        try:
            user = _make_user(session)
            prefs = UserNotificationPreferences(
                user_id=user.id,
                phone_number="+1234567890",
            )
            session.add(prefs)
            session.commit()

            headers = _token(user.id)
            response = client.patch(
                "/api/notifications/preferences",
                headers=headers,
                json={"phone_number": None}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["phone_number"] is None
        finally:
            session.close()

    def test_patch_preferences_without_token_returns_401_or_403(self, client):
        """PATCH /api/notifications/preferences without token returns 401 or 403."""
        response = client.patch(
            "/api/notifications/preferences",
            json={"email_enabled": False}
        )
        assert response.status_code in (401, 403)
