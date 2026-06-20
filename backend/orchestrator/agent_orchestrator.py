import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.database.models import Agent, AgentStatus
from backend.trading.trade_executor import TradeExecutor
from backend.llm.llm_router import LLMRouter
from backend.llm.config import read_config
from backend.trading.risk_manager import check_agent_risk
from backend.brokers.manager import get_connector
from backend.api.websocket import manager

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates agent lifecycle: scheduling, market data fetching, LLM decisions, trade execution."""

    def __init__(self, vault, db_session_factory):
        """
        Args:
            vault: EncryptedVault instance
            db_session_factory: sessionmaker that returns sync Session
        """
        self.vault = vault
        self.db_factory = db_session_factory
        self.scheduler = AsyncIOScheduler()
        self.executor = TradeExecutor(vault, None)

    async def initialize(self):
        """Load all active agents from DB, schedule with staggered starts, and start scheduler."""
        session = self.db_factory()
        try:
            agents = session.query(Agent).filter(Agent.is_active == True).all()
        finally:
            session.close()

        if not agents:
            logger.info("No active agents to schedule")
            return

        logger.info(f"Scheduling {len(agents)} active agents")

        for i, agent in enumerate(agents):
            check_freq = agent.check_frequency or 300
            stagger_offset = (i / max(len(agents), 1)) * check_freq
            start_date = datetime.now() + timedelta(seconds=stagger_offset)

            self.scheduler.add_job(
                self.run_agent,
                "interval",
                seconds=check_freq,
                args=[agent.id],
                id=f"agent_{agent.id}",
                replace_existing=True,
                start_date=start_date,
            )

            logger.info(
                f"scheduled agent {agent.id} ({agent.name}) "
                f"interval={check_freq}s start_offset={stagger_offset:.1f}s"
            )

        self.scheduler.start()
        logger.info("Agent scheduler started")

    async def shutdown(self):
        """Gracefully shut down scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Agent scheduler stopped")

    async def run_agent(self, agent_id: int):
        """Run a single agent: fetch market data, decide, check risk, execute."""
        session = self.db_factory()
        try:
            # Load agent
            agent = session.query(Agent).filter(Agent.id == agent_id).first()

            if not agent:
                logger.warning(f"agent {agent_id} not found")
                return

            # Skip if inactive or paused
            if not agent.is_active:
                logger.debug(f"agent {agent_id} inactive, skipping")
                return

            if agent.status == AgentStatus.PAUSED:
                logger.debug(f"agent {agent_id} paused, skipping")
                return

            # Set running and broadcast
            agent.status = AgentStatus.RUNNING
            agent.last_heartbeat = datetime.utcnow()
            session.add(agent)
            session.commit()

            await manager.broadcast({
                "event": "agent_update",
                "agent_id": agent.id,
                "status": agent.status.value,
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Get broker connector
            try:
                connector = get_connector(agent.broker, self.vault)
            except Exception as e:
                logger.error(f"agent {agent_id} broker error: {e}")
                agent.status = AgentStatus.ERROR
                session.add(agent)
                session.commit()
                await manager.broadcast({
                    "event": "agent_update",
                    "agent_id": agent.id,
                    "status": agent.status.value,
                })
                return

            # Fetch market data
            try:
                market_data_obj = await connector.get_market_data(agent.symbol)
                market_data = {
                    "price": market_data_obj.price,
                    "volume": market_data_obj.volume,
                    "rsi": market_data_obj.rsi,
                    "ma20": market_data_obj.ma20,
                    "ma50": market_data_obj.ma50,
                }
            except Exception as e:
                logger.error(f"agent {agent_id} market data error: {e}")
                agent.status = AgentStatus.ERROR
                session.add(agent)
                session.commit()
                await manager.broadcast({
                    "event": "agent_update",
                    "agent_id": agent.id,
                    "status": agent.status.value,
                })
                return

            # Load context from file if present
            context = ""
            if agent.context_file_path:
                try:
                    with open(agent.context_file_path, "r") as f:
                        context = f.read()
                except Exception as e:
                    logger.warning(f"agent {agent_id} context file read error: {e}")

            # Get LLM decision
            llm_cfg = read_config()
            claude_key = None
            openai_key = None
            try:
                claude_key = self.vault.get("anthropic_api_key")
            except Exception:
                pass
            try:
                openai_key = self.vault.get("openai_api_key")
            except Exception:
                pass
            router = LLMRouter.from_config(llm_cfg, claude_api_key=claude_key, openai_api_key=openai_key)

            decision = await router.decide(agent.symbol, market_data, context)

            logger.info(f"agent {agent_id} LLM decision: {decision.action} conf={decision.confidence:.0%}")

            # Check risk
            should_pause, risk_reason = check_agent_risk(
                agent_id=agent.id,
                confidence_score=agent.confidence_score,
                consecutive_losses=agent.consecutive_losses,
            )

            if should_pause:
                logger.warning(f"agent {agent_id} paused by risk: {risk_reason}")
                agent.status = AgentStatus.PAUSED
                session.add(agent)
                session.commit()
                await manager.broadcast({
                    "event": "agent_paused",
                    "agent_id": agent.id,
                    "reason": risk_reason,
                })
                return

            # Build agent config for trade executor
            agent_config = self._build_agent_config(agent)

            # Execute trade (TradeExecutor expects AsyncSession; wrap in sync adapter)
            exec_result = await self.executor.execute(
                agent_id=agent.id,
                decision=decision,
                agent_config=agent_config,
                vault=self.vault,
                db_session=session,
                broadcast_callback=manager.broadcast,
            )

            logger.info(f"agent {agent_id} execution result: {exec_result}")

            # Set status back to IDLE
            agent.status = AgentStatus.IDLE
            session.add(agent)
            session.commit()

            await manager.broadcast({
                "event": "agent_update",
                "agent_id": agent.id,
                "status": agent.status.value,
                "last_execution": exec_result,
                "timestamp": datetime.utcnow().isoformat(),
            })

        except Exception as e:
            logger.exception(f"agent {agent_id} fatal error: {e}")
            # Try to set error status
            try:
                agent = session.query(Agent).filter(Agent.id == agent_id).first()
                if agent:
                    agent.status = AgentStatus.ERROR
                    session.add(agent)
                    session.commit()
                    await manager.broadcast({
                        "event": "agent_update",
                        "agent_id": agent.id,
                        "status": agent.status.value,
                    })
            except Exception as inner_e:
                logger.error(f"failed to set error status for agent {agent_id}: {inner_e}")
        finally:
            session.close()

    def _build_agent_config(self, agent: Agent) -> dict:
        """Extract agent configuration for trade executor."""
        return {
            "broker": agent.broker,
            "paper_trading": agent.is_paper_trading,
            "allocation_percent": 0.1,  # default 10% of balance
            "max_position_size": agent.max_position_size,
            "asset": agent.symbol,
            "execution_mode": agent.execution_mode,
        }
