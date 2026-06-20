import pytest
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.models import Base, User
from backend.auth.utils import hash_password, verify_password


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_user_model_creation(db_session):
    user = User(
        id=str(uuid4()),
        username="alice",
        email="alice@example.com",
        hashed_password="fake_hash",
        role="trader",
    )
    db_session.add(user)
    db_session.commit()
    retrieved = db_session.query(User).filter_by(username="alice").first()
    assert retrieved is not None
    assert retrieved.email == "alice@example.com"
    assert retrieved.role == "trader"
    assert retrieved.created_at is not None


def test_user_username_unique(db_session):
    user1 = User(id=str(uuid4()), username="bob", email="bob@example.com", hashed_password="hash1", role="trader")
    db_session.add(user1)
    db_session.commit()
    user2 = User(id=str(uuid4()), username="bob", email="bob2@example.com", hashed_password="hash2", role="trader")
    db_session.add(user2)
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_email_unique(db_session):
    user1 = User(id=str(uuid4()), username="charlie", email="charlie@example.com", hashed_password="hash1", role="trader")
    db_session.add(user1)
    db_session.commit()
    user2 = User(id=str(uuid4()), username="charlie2", email="charlie@example.com", hashed_password="hash2", role="trader")
    db_session.add(user2)
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_hash_password_returns_string():
    hashed = hash_password("my_secure_password_123")
    assert isinstance(hashed, str)
    assert hashed != "my_secure_password_123"
    assert len(hashed) > 20


def test_verify_password_correct():
    plain = "my_secure_password_123"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("my_secure_password_123")
    assert verify_password("wrong_password", hashed) is False


def test_verify_password_empty_string():
    hashed = hash_password("password")
    assert verify_password("", hashed) is False
