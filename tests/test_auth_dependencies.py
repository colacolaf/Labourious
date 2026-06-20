import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database.models import Base, User, UserRole
from backend.auth.utils import hash_password, create_access_token
from backend.auth import dependencies as deps_module


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture
def test_user(test_db):
    """Create a test user."""
    user = User(
        id="user-test-1",
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.TRADER,
    )
    test_db.add(user)
    test_db.commit()
    return user


@pytest.fixture
def admin_user(test_db):
    """Create a test admin user."""
    user = User(
        id="admin-test-1",
        username="adminuser",
        email="admin@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.ADMIN,
    )
    test_db.add(user)
    test_db.commit()
    return user


@pytest.fixture
def client(test_db):
    """Override the _get_db dependency and return TestClient."""
    original_get_db = deps_module._get_db

    def override_get_db():
        try:
            yield test_db
        finally:
            pass  # test_db manages its own lifecycle

    app.dependency_overrides[deps_module._get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.pop(deps_module._get_db, None)


class TestGetCurrentUser:
    def test_health_endpoint_unprotected(self, client):
        """Health endpoint should be accessible without auth."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_no_token_returns_403(self, client):
        """Missing Authorization header → 403 from HTTPBearer."""
        # Add a test protected route
        test_router = APIRouter()

        @test_router.get("/test-protected")
        async def protected(user=Depends(deps_module.get_current_user)):
            return {"user": user.username}

        app.include_router(test_router)

        response = client.get("/test-protected")
        # HTTPBearer behavior: missing credentials returns 403
        assert response.status_code in (401, 403)
        data = response.json()
        assert "detail" in data

    def test_invalid_token_returns_401(self, client):
        """Invalid token → 401."""
        test_router = APIRouter()

        @test_router.get("/test-protected-invalid")
        async def protected_invalid(user=Depends(deps_module.get_current_user)):
            return {"user": user.username}

        app.include_router(test_router)

        response = client.get(
            "/test-protected-invalid",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired token"

    def test_valid_token_returns_user(self, client, test_user):
        """Valid token should return user object."""
        token = create_access_token({"sub": test_user.id})
        test_router = APIRouter()

        @test_router.get("/test-protected-valid")
        async def protected_valid(user=Depends(deps_module.get_current_user)):
            return {"user_id": user.id, "username": user.username, "role": user.role}

        app.include_router(test_router)

        response = client.get(
            "/test-protected-valid", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["username"] == test_user.username
        assert data["role"] == UserRole.TRADER

    def test_nonexistent_user_returns_401(self, client):
        """Token for non-existent user → 401."""
        token = create_access_token({"sub": "nonexistent-user-id"})
        test_router = APIRouter()

        @test_router.get("/test-nonexistent-user")
        async def protected_nonexistent(user=Depends(deps_module.get_current_user)):
            return {"user": user.username}

        app.include_router(test_router)

        response = client.get(
            "/test-nonexistent-user", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "User not found"


class TestRequireRole:
    def test_trader_access_trader_endpoint(self, client, test_user):
        """Trader user can access trader-only endpoint."""
        token = create_access_token({"sub": test_user.id})
        test_router = APIRouter()

        @test_router.get("/test-trader-only")
        async def trader_only(
            user=Depends(deps_module.require_role(UserRole.TRADER))
        ):
            return {"role": user.role}

        app.include_router(test_router)

        response = client.get(
            "/test-trader-only", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == UserRole.TRADER

    def test_trader_cannot_access_admin_endpoint(self, client, test_user):
        """Trader user cannot access admin-only endpoint."""
        token = create_access_token({"sub": test_user.id})
        test_router = APIRouter()

        @test_router.get("/test-admin-only")
        async def admin_only(user=Depends(deps_module.require_role(UserRole.ADMIN))):
            return {"role": user.role}

        app.include_router(test_router)

        response = client.get(
            "/test-admin-only", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"

    def test_admin_access_admin_endpoint(self, client, admin_user):
        """Admin user can access admin-only endpoint."""
        token = create_access_token({"sub": admin_user.id})
        test_router = APIRouter()

        @test_router.get("/test-admin-only-success")
        async def admin_only_success(
            user=Depends(deps_module.require_role(UserRole.ADMIN))
        ):
            return {"role": user.role}

        app.include_router(test_router)

        response = client.get(
            "/test-admin-only-success", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == UserRole.ADMIN

    def test_multiple_allowed_roles(self, client, test_user, admin_user):
        """Endpoint with multiple allowed roles works correctly."""
        test_router = APIRouter()

        @test_router.get("/test-multi-role")
        async def multi_role(
            user=Depends(deps_module.require_role(UserRole.ADMIN, UserRole.TRADER))
        ):
            return {"role": user.role}

        app.include_router(test_router)

        # Test with trader token
        trader_token = create_access_token({"sub": test_user.id})
        response = client.get(
            "/test-multi-role", headers={"Authorization": f"Bearer {trader_token}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == UserRole.TRADER

        # Test with admin token
        admin_token = create_access_token({"sub": admin_user.id})
        response = client.get(
            "/test-multi-role", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == UserRole.ADMIN
