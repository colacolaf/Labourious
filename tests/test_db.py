import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base, Agent


def _make_engine(db_path: str):
    """Create a fresh engine for a test DB — bypasses the module singleton."""
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine


def test_db_tables_created(temp_db_path):
    engine = _make_engine(temp_db_path)
    assert os.path.exists(temp_db_path)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
    assert "agents" in tables
    assert "trades" in tables
    assert "performance" in tables


def test_agent_crud(temp_db_path):
    engine = _make_engine(temp_db_path)
    Session = sessionmaker(bind=engine)
    session = Session()

    agent = Agent(
        name="test-agent",
        symbol="BTC/USD",
        exchange="kraken",
        timeframe="1h",
    )
    session.add(agent)
    session.commit()

    fetched = session.query(Agent).filter_by(name="test-agent").first()
    assert fetched is not None
    assert fetched.symbol == "BTC/USD"
    assert fetched.is_paper_trading is True

    session.close()
