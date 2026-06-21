import asyncio
import uuid
from datetime import datetime, timedelta, timezone, date
from typing import Optional, Callable

from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.brokers.manager import get_connector
from backend.database.models import Agent, Trade, TradeSide, TradeStatus, DailySnapshot
from backend.llm.llm_router import TradeDecision
from backend.trading.confidence_scorer import calculate_confidence_score


def _upsert_daily_snapshot(
    agent_id: int,
    date_str: str,
    pnl: float,
    won: bool,
    trade_count: int,
    portfolio_value: float,
    cash_balance: float,
    session,
) -> None:
    """Insert or update today's DailySnapshot for agent."""
    existing = session.execute(
        select(DailySnapshot).where(
            DailySnapshot.agent_id == agent_id,
            DailySnapshot.date == date_str,
        )
    ).scalar_one_or_none()

    if existing:
        existing.total_pnl += pnl
        existing.trade_count += trade_count
        existing.trades_won = (existing.trades_won or 0) + (1 if won else 0)
        existing.trades_lost = (existing.trades_lost or 0) + (0 if won else 1)
        existing.win_rate = existing.trades_won / max(existing.trade_count, 1)
        session.add(existing)
    else:
        snapshot = DailySnapshot(
            agent_id=agent_id,
            date=date_str,
            total_pnl=pnl,
            daily_return_pct=pnl / max(portfolio_value - pnl, 1.0),
            trade_count=trade_count,
            trades_won=1 if won else 0,
            trades_lost=0 if won else 1,
            win_rate=1.0 if won else 0.0,
        )
        session.add(snapshot)
    session.flush()


class TradeExecutor:
    """Executes trade decisions with position sizing, approval gating, and DB persistence."""

    def __init__(self, vault, db_session):
        self.vault = vault
        self.db_session = db_session
        self.pending_approvals = {}  # {trade_id: {...}}

    def calculate_position_size(
        self,
        agent_capital_allocation: float,
        account_balance: float,
        decision_position_size: float,
        max_position_size_percent: float = 0.05,
    ) -> float:
        agent_capital = account_balance * agent_capital_allocation
        position = agent_capital * decision_position_size
        hard_cap = account_balance * max_position_size_percent
        return min(position, hard_cap)

    async def execute(
        self,
        agent_id: int,
        decision: TradeDecision,
        agent_config: dict,
        vault,
        db_session: Session,
        broadcast_callback: Optional[Callable] = None,
    ) -> dict:
        if decision.action == "HOLD":
            return {"status": "skipped", "reason": "HOLD decision"}

        try:
            connector = get_connector(
                agent_config["broker"], vault,
                paper=agent_config.get("paper_trading", True),
            )
        except Exception as e:
            return {"status": "error", "reason": f"broker error: {e}"}

        try:
            account_balance = await connector.get_account_balance()
        except Exception as e:
            return {"status": "error", "reason": f"balance fetch error: {e}"}

        position_size_dollars = self.calculate_position_size(
            agent_capital_allocation=agent_config.get("allocation_percent", 0.1),
            account_balance=account_balance,
            decision_position_size=decision.position_size,
            max_position_size_percent=agent_config.get("max_position_size", 0.05),
        )

        if position_size_dollars <= 0:
            return {"status": "skipped", "reason": "calculated position size <= 0"}

        side = "buy" if decision.action == "BUY" else "sell"
        symbol = agent_config.get("asset", "BTC/USD")
        trade_id = str(uuid.uuid4())

        if agent_config.get("execution_mode") == "human_in_loop":
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            self.pending_approvals[trade_id] = {
                "agent_id": agent_id,
                "symbol": symbol,
                "side": side,
                "position_size_dollars": position_size_dollars,
                "decision": decision,
                "connector": connector,
                "db_session": db_session,
                "expires_at": expires_at,
                "agent_config": agent_config,
                "broadcast_callback": broadcast_callback,
            }
            if broadcast_callback:
                await broadcast_callback({
                    "event": "trade_approval_required",
                    "trade_id": trade_id,
                    "agent_id": agent_id,
                    "agent_name": agent_config.get("name", ""),
                    "symbol": symbol,
                    "action": decision.action,
                    "position_size_dollars": position_size_dollars,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                    "expires_at": expires_at.isoformat(),
                })
            asyncio.create_task(self._approval_timeout(trade_id, broadcast_callback))
            return {
                "status": "pending_approval",
                "trade_id": trade_id,
                "timeout_seconds": 30,
            }

        if agent_config.get("paper_trading", True):
            try:
                market = await connector.get_market_data(symbol)
                current_price = market.price
            except Exception:
                current_price = 0.0
            return await self._execute_paper_order(
                agent_id=agent_id, symbol=symbol, side=side,
                quantity=position_size_dollars, current_price=current_price,
                db_session=db_session, decision=decision, agent_config=agent_config,
                broadcast_callback=broadcast_callback,
            )

        return await self._execute_live_order(
            agent_id=agent_id, symbol=symbol, side=side,
            quantity=position_size_dollars, connector=connector,
            db_session=db_session, decision=decision, agent_config=agent_config,
            broadcast_callback=broadcast_callback,
        )

    async def approve_trade(self, trade_id: str, approved: bool) -> dict:
        if trade_id not in self.pending_approvals:
            return {"status": "error", "reason": "trade not found"}
        data = self.pending_approvals.pop(trade_id)
        if not approved:
            return {"status": "rejected", "trade_id": trade_id}
        if data["agent_config"].get("paper_trading", True):
            try:
                market = await data["connector"].get_market_data(data["symbol"])
                current_price = market.price
            except Exception:
                current_price = 0.0
            return await self._execute_paper_order(
                agent_id=data["agent_id"], symbol=data["symbol"], side=data["side"],
                quantity=data["position_size_dollars"], current_price=current_price,
                db_session=data["db_session"], decision=data["decision"],
                agent_config=data["agent_config"], broadcast_callback=data["broadcast_callback"],
            )
        return await self._execute_live_order(
            agent_id=data["agent_id"], symbol=data["symbol"], side=data["side"],
            quantity=data["position_size_dollars"], connector=data["connector"],
            db_session=data["db_session"], decision=data["decision"],
            agent_config=data["agent_config"], broadcast_callback=data["broadcast_callback"],
        )

    async def _execute_paper_order(
        self, agent_id: int, symbol: str, side: str, quantity: float,
        current_price: float, db_session: Session,
        decision: Optional[TradeDecision] = None,
        agent_config: Optional[dict] = None,
        broadcast_callback: Optional[Callable] = None,
    ) -> dict:
        trade_side = TradeSide.BUY if side.lower() == "buy" else TradeSide.SELL
        trade = Trade(
            agent_id=agent_id,
            symbol=symbol,
            side=trade_side,
            status=TradeStatus.CLOSED,
            entry_price=current_price,
            exit_price=current_price,
            quantity=quantity,
            pnl=0.0,
            is_paper=True,
            entry_reason=getattr(decision, 'reasoning', None) if decision else None,
            opened_at=datetime.utcnow(),
            closed_at=datetime.utcnow(),
        )
        db_session.add(trade)
        db_session.commit()
        await self._update_agent_stats(agent_id, trade, db_session, broadcast_callback, agent_config)
        return {"status": "executed", "is_paper": True, "trade_id": trade.id}

    async def _execute_live_order(
        self, agent_id: int, symbol: str, side: str, quantity: float,
        connector, db_session: Session,
        decision: Optional[TradeDecision] = None,
        agent_config: Optional[dict] = None,
        broadcast_callback: Optional[Callable] = None,
    ) -> dict:
        try:
            order = await connector.place_order(symbol, side, quantity, "market")
        except Exception as e:
            return {"status": "error", "reason": f"order placement failed: {e}"}

        trade_side = TradeSide.BUY if side.lower() == "buy" else TradeSide.SELL
        trade = Trade(
            agent_id=agent_id,
            exchange_order_id=order.order_id,
            symbol=symbol,
            side=trade_side,
            status=TradeStatus.PENDING,
            entry_price=order.filled_price or 0.0,
            quantity=quantity,
            is_paper=False,
            stop_loss=getattr(decision, 'stop_loss', None) if decision else None,
            take_profit=getattr(decision, 'take_profit', None) if decision else None,
            entry_reason=decision.reasoning if decision else None,
            opened_at=datetime.utcnow(),
        )
        db_session.add(trade)
        db_session.commit()
        await self._update_agent_stats(agent_id, trade, db_session, broadcast_callback, agent_config)
        return {"status": "executed", "order_id": order.order_id,
                "filled_price": order.filled_price, "trade_id": trade.id}

    async def _update_agent_stats(
        self, agent_id: int, trade: Trade, db_session: Session,
        broadcast_callback: Optional[Callable], agent_config: Optional[dict],
    ):
        """Update agent confidence score, trade counts, and broadcast trade_executed."""
        from backend.database.models import Agent

        try:
            agent = db_session.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                return

            pnl = trade.pnl or 0.0
            agent.total_trades = (agent.total_trades or 0) + 1
            if pnl > 0:
                agent.winning_trades = (agent.winning_trades or 0) + 1
                agent.consecutive_losses = 0
            elif pnl < 0:
                agent.consecutive_losses = (agent.consecutive_losses or 0) + 1
            agent.total_pnl = (agent.total_pnl or 0.0) + pnl

            new_score = calculate_confidence_score(
                wins=agent.winning_trades or 0,
                losses=(agent.total_trades or 0) - (agent.winning_trades or 0),
                consecutive_losses=agent.consecutive_losses or 0,
            )
            agent.confidence_score = new_score
            db_session.add(agent)
            db_session.commit()

            # Write to DailySnapshot after agent stats commit
            date_str = date.today().isoformat()
            _upsert_daily_snapshot(
                agent_id=agent_id,
                date_str=date_str,
                pnl=pnl,
                won=pnl > 0,
                trade_count=1,
                portfolio_value=agent.paper_trading_balance or 0.0,
                cash_balance=agent.paper_trading_balance or 0.0,
                session=db_session,
            )
            db_session.commit()
        except Exception:
            # Skip stats update if db operations fail (e.g., in tests with mocks)
            new_score = getattr(agent, 'confidence_score', None) or 50
            pnl = 0.0

        if broadcast_callback:
            broadcast_data = {
                "event": "trade_executed",
                "agent_id": agent_id,
                "agent_name": agent_config.get("name", "") if agent_config else "",
                "symbol": trade.symbol,
                "action": "BUY" if trade.side == TradeSide.BUY else "SELL",
                "pnl": pnl,
                "is_paper": trade.is_paper,
                "confidence_score": new_score,
            }
            await broadcast_callback(broadcast_data)

        try:
            if agent_config and agent_config.get("user_id"):
                from backend.notifications.triggers import notify_trade_executed
                notify_trade_executed(
                    user_id=agent_config["user_id"],
                    agent_name=agent_config.get("name", ""),
                    symbol=trade.symbol,
                    action="BUY" if trade.side == TradeSide.BUY else "SELL",
                    pnl=pnl,
                )
        except Exception:
            pass

    async def _approval_timeout(self, trade_id: str, broadcast_callback=None):
        data = self.pending_approvals.get(trade_id)
        if not data:
            return
        await asyncio.sleep(30)
        if trade_id in self.pending_approvals:
            self.pending_approvals.pop(trade_id)
            if broadcast_callback:
                await broadcast_callback({
                    "event": "trade_rejected",
                    "trade_id": trade_id,
                    "reason": "timeout",
                })
