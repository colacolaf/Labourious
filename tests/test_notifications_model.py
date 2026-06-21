"""4B.1: UserNotificationPreferences model tests."""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from backend.database.models import Base, User, UserRole
from backend.notifications.models import UserNotificationPreferences


_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_engine)
_Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def clear_db():
    """Clear database between tests."""
    session = _Session()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()


@pytest.fixture
def session():
    """Provide a clean session for each test."""
    s = _Session()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


class TestUserNotificationPreferences:
    """Test UserNotificationPreferences model."""

    def test_create_notification_preferences(self, session):
        """Can create notification preferences for a user."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.TRADER,
        )
        session.add(user)
        session.commit()

        prefs = UserNotificationPreferences(user_id=user.id)
        session.add(prefs)
        session.commit()

        result = session.query(UserNotificationPreferences).filter_by(user_id=user.id).first()
        assert result is not None
        assert result.user_id == user.id

    def test_default_values(self, session):
        """All boolean defaults are correct."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.TRADER,
        )
        session.add(user)
        session.commit()

        prefs = UserNotificationPreferences(user_id=user.id)
        session.add(prefs)
        session.commit()

        result = session.query(UserNotificationPreferences).filter_by(user_id=user.id).first()
        assert result.email_enabled is True
        assert result.sms_enabled is False
        assert result.notify_on_trade is True
        assert result.notify_on_agent_pause is True
        assert result.notify_on_drawdown is True
        assert result.daily_digest is False

    def test_unique_user_id_constraint(self, session):
        """user_id unique constraint enforced."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.TRADER,
        )
        session.add(user)
        session.commit()

        prefs1 = UserNotificationPreferences(user_id=user.id)
        session.add(prefs1)
        session.commit()

        prefs2 = UserNotificationPreferences(user_id=user.id)
        session.add(prefs2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_cascade_delete_on_user_delete(self, session):
        """Deleting user cascades to notification preferences."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.TRADER,
        )
        session.add(user)
        session.commit()

        prefs = UserNotificationPreferences(user_id=user.id)
        session.add(prefs)
        session.commit()

        # Verify prefs exist
        result = session.query(UserNotificationPreferences).filter_by(user_id=user.id).first()
        assert result is not None

        # Delete user
        session.delete(user)
        session.commit()

        # Verify prefs are deleted
        result = session.query(UserNotificationPreferences).filter_by(user_id=user.id).first()
        assert result is None

    def test_user_relationship(self, session):
        """User.notification_preferences relationship works."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.TRADER,
        )
        session.add(user)
        session.commit()

        prefs = UserNotificationPreferences(user_id=user.id)
        session.add(prefs)
        session.commit()

        # Refresh to load relationship
        user_result = session.query(User).filter_by(id=user.id).first()
        assert user_result.notification_preferences is not None
        assert user_result.notification_preferences.user_id == user.id

    def test_timestamps_created_automatically(self, session):
        """created_at and updated_at are set automatically."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.TRADER,
        )
        session.add(user)
        session.commit()

        prefs = UserNotificationPreferences(user_id=user.id)
        session.add(prefs)
        session.commit()

        result = session.query(UserNotificationPreferences).filter_by(user_id=user.id).first()
        assert result.created_at is not None
        assert result.updated_at is not None
        assert isinstance(result.created_at, datetime)
        assert isinstance(result.updated_at, datetime)
