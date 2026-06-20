import pytest




def test_run_eod_snapshot_writes_row(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"

    # Bootstrap real tables
    from backend.database.db import init_db, get_db_session
    from backend.database.models import Agent, AgentStatus, AgentType, DailySnapshot, Trade, TradeSide, TradeStatus
    from sqlalchemy import select

    init_db(db_url)

    with get_db_session(db_url) as session:
        agent = Agent(
            name="TestAgent",
            agent_type=AgentType.CUSTOM,
            symbol="BTC/USD",
            total_pnl=500.0,
            total_trades=5,
            winning_trades=3,
        )
        session.add(agent)
        session.commit()
        agent_id = agent.id

        # Create 3 closed trades with positive pnl (wins)
        for i in range(3):
            trade = Trade(
                agent_id=agent_id,
                symbol="BTC/USD",
                side=TradeSide.BUY,
                entry_price=100.0,
                quantity=1.0,
                status=TradeStatus.CLOSED,
                pnl=50.0,
                closed_at=datetime.now()
            )
            session.add(trade)

        # Create 2 closed trades with negative pnl (losses)
        for i in range(2):
            trade = Trade(
                agent_id=agent_id,
                symbol="BTC/USD",
                side=TradeSide.BUY,
                entry_price=100.0,
                quantity=1.0,
                status=TradeStatus.CLOSED,
                pnl=-25.0,
                closed_at=datetime.now()
            )
            session.add(trade)
        session.commit()

    from backend.analytics.snapshot_job import run_eod_snapshot
    run_eod_snapshot(db_url)

    with get_db_session(db_url) as session:
        snapshots = session.execute(
            select(DailySnapshot).where(DailySnapshot.agent_id == agent_id)
        ).scalars().all()

        assert len(snapshots) == 1
        assert snapshots[0].total_pnl == 500.0
        assert snapshots[0].trade_count == 5
        assert snapshots[0].win_rate == 60.0  # 3 wins out of 5 trades


def test_run_eod_snapshot_idempotent(tmp_path):
    """Running twice on same day should not duplicate rows."""
    db_url = f"sqlite:///{tmp_path}/test.db"

    from backend.database.db import init_db, get_db_session
    from backend.database.models import Agent, AgentType, DailySnapshot
    from sqlalchemy import select

    init_db(db_url)

    with get_db_session(db_url) as session:
        agent = Agent(name="TestAgent2", agent_type=AgentType.CUSTOM, symbol="ETH/USD")
        session.add(agent)
        session.commit()

    from backend.analytics.snapshot_job import run_eod_snapshot
    run_eod_snapshot(db_url)
    run_eod_snapshot(db_url)

    with get_db_session(db_url) as session:
        count = session.execute(select(DailySnapshot)).scalars().all()

    assert len(count) == 1
