import pytest
from datetime import timedelta
from pydantic import ValidationError
from backend.auth.schemas import UserCreate, UserLogin, UserOut, TokenResponse
from backend.auth.utils import create_access_token, create_refresh_token, decode_token


def test_user_create_schema():
    data = UserCreate(username="alice", email="alice@example.com", password="secure123")
    assert data.username == "alice"
    assert data.email == "alice@example.com"


def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(username="alice", email="not-an-email", password="secure123")


def test_user_out_no_password():
    data = UserOut(id="user-123", username="alice", email="alice@example.com", role="trader")
    assert "password" not in data.model_dump()


def test_token_response_schema():
    data = TokenResponse(access_token="token123", refresh_token="refresh123", token_type="bearer")
    assert data.access_token == "token123"
    assert data.token_type == "bearer"


def test_create_access_token():
    token = create_access_token({"sub": "alice"})
    assert isinstance(token, str)
    assert len(token) > 20


def test_decode_token_valid():
    token = create_access_token({"sub": "alice"}, expires_delta=timedelta(minutes=30))
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded.get("sub") == "alice"


def test_decode_token_expired():
    token = create_access_token({"sub": "alice"}, expires_delta=timedelta(seconds=-1))
    assert decode_token(token) is None


def test_decode_token_invalid():
    assert decode_token("invalid.token.here") is None


def test_create_refresh_token():
    refresh = create_refresh_token({"sub": "alice"}, expires_delta=timedelta(days=7))
    assert isinstance(refresh, str)
    decoded = decode_token(refresh)
    assert decoded is not None
    assert decoded.get("type") == "refresh"
