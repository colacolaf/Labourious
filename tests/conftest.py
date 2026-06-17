import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def temp_db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture(scope="function")
def temp_vault_path(tmp_path):
    return str(tmp_path / "test_vault.db")
