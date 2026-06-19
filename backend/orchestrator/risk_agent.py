"""Portfolio-level risk meta-agent. Monitors portfolio drawdown and pauses all agents on breach."""

from sqlalchemy import select
from backend.database.models import Agent, AgentStatus
from backend.api.websocket import manager


class RiskAgent:
    """Portfolio meta-agent: monitors drawdown, pauses agents on breach."""
    MAX_PORTFOLIO_DRAWDOWN = -0.25

    def __init__(self, db_session_factory):
        self.db_factory = db_session_factory

    async def run(self):
        """Monitor portfolio and pause all agents if drawdown exceeds threshold."""
        async with self.db_factory() as session:
            result = await session.execute(select(Agent).where(Agent.is_active == True))
            agents = result.scalars().all()
            stats = self._compute_stats(agents)

            if stats["portfolio_drawdown"] < self.MAX_PORTFOLIO_DRAWDOWN:
                await self._pause_all_agents(
                    agents, session,
                    f"Portfolio drawdown {stats['portfolio_drawdown']:.2%} < {self.MAX_PORTFOLIO_DRAWDOWN:.2%}"
                )
                return

            await manager.broadcast({
                "type": "portfolio_update",
                "total_pnl": stats["total_pnl"],
                "total_capital": stats["total_capital"],
                "portfolio_drawdown": stats["portfolio_drawdown"],
                "agent_count": stats["agent_count"],
                "paused_count": stats["paused_count"],
            })

    def _compute_stats(self, agents: list) -> dict:
        """Compute portfolio drawdown and agent counts."""
        total_pnl = sum(agent.total_pnl for agent in agents)
        total_capital = sum(agent.paper_trading_balance for agent in agents)
        portfolio_drawdown = (total_pnl / total_capital) if total_capital > 0 else 0.0
        paused_count = sum(1 for agent in agents if agent.status == AgentStatus.PAUSED)

        return {
            "total_pnl": total_pnl,
            "total_capital": total_capital,
            "portfolio_drawdown": portfolio_drawdown,
            "agent_count": len(agents),
            "paused_count": paused_count,
        }

    async def _pause_all_agents(self, agents: list, session, reason: str):
        """Pause all agents and broadcast alerts."""
        for agent in agents:
            agent.status = AgentStatus.PAUSED
            await manager.broadcast({
                "type": "agent_paused",
                "agent_id": agent.id,
                "agent_name": agent.name,
                "reason": reason,
            })

        await session.commit()
        await manager.broadcast({
            "type": "risk_alert",
            "message": reason,
            "paused_agents": len(agents),
        })
