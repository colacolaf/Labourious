import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from backend.brokers.manager import get_connector
from backend.database.models import Trade, TradeSide, TradeStatus
from backend.llm.llm_router import TradeDecision


class TradeExecutor:
    """Executes trade decisions with position sizing, approval gating, and DB persistence."""

    def __init__(self, vault, db_session: AsyncSession):
        self.vault = vault
        self.db_session = db_session
        self.pending_approvals = {}  # {trade_id: {timeout_at, agent_id, decision, ...}}

    def calculate_position_size(
        self,
        agent_capital_allocation: float,
        account_balance: float,
        decision_position_size: float,
        max_position_size_percent: float = 0.05,
    ) -> float:
        """Calculate position size in dollars, capped by hard limit."""
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
        db_session: AsyncSession,
        broadcast_callback: Optional[Callable] = None,
    ) -> dict:
        """Execute trade or queue for approval."""
        if decision.action == "HOLD":
            return {"status": "skipped", "reason": "HOLD decision"}

        try:
            connector = get_connector(agent_config["broker"], vault)
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
            timeout_at = datetime.utcnow() + timedelta(seconds=30)
            self.pending_approvals[trade_id] = {
                "agent_id": agent_id,
                "symbol": symbol,
                "side": side,
                "position_size_dollars": position_size_dollars,
                "decision": decision,
                "connector": connector,
                "db_session": db_session,
                "timeout_at": timeout_at,
            }
            if broadcast_callback:
                await broadcast_callback(
                    {
                        "event": "trade_pending_approval",
                        "trade_id": trade_id,
                        "agent_id": agent_id,
                        "symbol": symbol,
                        "side": side,
                        "position_size": position_size_dollars,
                    }
                )
            asyncio.create_task(self._approval_timeout(trade_id))
            return {
                "status": "pending_approval",
                "trade_id": trade_id,
                "timeout_seconds": 30,
            }

        return await self._execute_live_order(
            agent_id=agent_id,
            symbol=symbol,
            side=side,
            quantity=position_size_dollars,
            connector=connector,
            db_session=db_session,
            decision=decision,
            agent_config=agent_config,
        )

    async def approve_trade(self, trade_id: str, approved: bool, agent_config: dict = None) -> dict:
        """Approve or reject a pending trade."""
        if trade_id not in self.pending_approvals:
            return {"status": "error", "reason": "trade not found"}

        data = self.pending_approvals.pop(trade_id)

        if not approved:
            return {"status": "rejected", "trade_id": trade_id}

        return await self._execute_live_order(
            agent_id=data["agent_id"],
            symbol=data["symbol"],
            side=data["side"],
            quantity=data["position_size_dollars"],
            connector=data["connector"],
            db_session=data["db_session"],
            decision=data["decision"],
            agent_config=agent_config,
        )

    async def _execute_live_order(
        self,
        agent_id: int,
        symbol: str,
        side: str,
        quantity: float,
        connector,
        db_session: AsyncSession,
        decision: Optional[TradeDecision] = None,
        agent_config: Optional[dict] = None,
    ) -> dict:
        """Place order via broker and persist to DB."""
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
            stop_loss=decision.stop_loss if decision else None,
            take_profit=decision.take_profit if decision else None,
            entry_reason=decision.reasoning if decision else None,
            opened_at=datetime.utcnow(),
        )

        db_session.add(trade)
        await db_session.commit()

        try:
            if agent_config and agent_config.get("user_id"):
                from backend.notifications.triggers import notify_trade_executed
                notify_trade_executed(
                    user_id=agent_config["user_id"],
                    agent_name=agent_config.get("name", ""),
                    symbol=symbol,
                    action="BUY" if side.lower() == "buy" else "SELL",
                    pnl=0.0,
                )
        except Exception:
            pass

        return {
            "status": "executed",
            "order_id": order.order_id,
            "filled_price": order.filled_price,
            "trade_id": trade.id,
        }

    async def _approval_timeout(self, trade_id: str):
        """Reject trade if not approved within 30 seconds."""
        data = self.pending_approvals.get(trade_id)
        if not data:
            return

        await asyncio.sleep(30)

        if trade_id in self.pending_approvals:
            self.pending_approvals.pop(trade_id)
