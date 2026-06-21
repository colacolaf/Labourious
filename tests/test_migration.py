import pytest
from sqlalchemy import create_engine, inspect
from backend.database.models import Base


@pytest.fixture
def engine(tmp_path):
    e = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(e)
    return e


def test_agent_phase2_columns(engine):
    cols = {c["name"] for c in inspect(engine).get_columns("agents")}
    expected = {"room", "broker", "context_file_path", "confidence_score",
                "execution_mode", "check_frequency", "paper_trading_balance",
                "consecutive_losses", "grid_col", "grid_row", "use_local_llm"}
    assert expected.issubset(cols)


def test_new_tables_exist(engine):
    tables = set(inspect(engine).get_table_names())
    assert {"broker_configs", "logs", "pending_approvals"}.issubset(tables)


@pytest.fixture
def db_session(engine):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_trade_has_is_paper_column(db_session):
    """Trade model exposes is_paper field."""
    from backend.database.models import Trade, TradeSide, TradeStatus
    t = Trade(
        agent_id=1, symbol="AAPL", side=TradeSide.BUY,
        status=TradeStatus.PENDING, entry_price=100.0, quantity=1.0,
        is_paper=True,
    )
    assert t.is_paper is True
