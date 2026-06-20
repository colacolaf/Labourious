import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.database.models import Base, User, UserRole
from backend.auth.utils import hash_password, create_access_token, create_refresh_token
from backend.auth import dependencies as deps_module

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    app.dependency_overrides[deps_module._get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.pop(deps_module._get_db, None)

@pytest.fixture
def admin_user(test_db):
    user = User(
        id="admin-1",
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("adminpass123"),
        role=UserRole.ADMIN,
    )
    test_db.add(user)
    test_db.commit()
    return user

@pytest.fixture
def trader_user(test_db):
    user = User(
        id="trader-1",
        username="trader",
        email="trader@example.com",
        hashed_password=hash_password("traderpass123"),
        role=UserRole.TRADER,
    )
    test_db.add(user)
    test_db.commit()
    return user

def test_register_success(client):
    response = client.post("/api/auth/register", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "SecurePass123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert "password" not in data

def test_register_duplicate_username(client, trader_user):
    response = client.post("/api/auth/register", json={
        "username": "trader",
        "email": "other@example.com",
        "password": "SecurePass123"
    })
    assert response.status_code == 409

def test_register_invalid_email(client):
    response = client.post("/api/auth/register", json={
        "username": "newuser",
        "email": "not-an-email",
        "password": "SecurePass123"
    })
    assert response.status_code == 422

def test_login_success(client, trader_user):
    response = client.post("/api/auth/login", json={
        "email": "trader@example.com",
        "password": "traderpass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client, trader_user):
    response = client.post("/api/auth/login", json={
        "email": "trader@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_login_nonexistent_user(client):
    response = client.post("/api/auth/login", json={
        "email": "ghost@example.com",
        "password": "password"
    })
    assert response.status_code == 401

def test_refresh_token(client, trader_user):
    login_resp = client.post("/api/auth/login", json={
        "email": "trader@example.com",
        "password": "traderpass123"
    })
    refresh_token = login_resp.json()["refresh_token"]
    response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_refresh_with_access_token_fails(client, trader_user):
    """Cannot use access token as refresh token."""
    access_token = create_access_token({"sub": trader_user.id})
    response = client.post("/api/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401

def test_me_endpoint(client, trader_user):
    token = create_access_token({"sub": trader_user.id})
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "trader"

def test_me_without_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401  # HTTPBearer returns 401 when no header

def test_users_list_admin(client, admin_user, trader_user):
    token = create_access_token({"sub": admin_user.id})
    response = client.get("/api/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) >= 2

def test_users_list_trader_forbidden(client, trader_user):
    token = create_access_token({"sub": trader_user.id})
    response = client.get("/api/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
