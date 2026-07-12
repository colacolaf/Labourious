from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from pathlib import Path
from backend.config import settings
from backend.database.db import init_db, get_session_factory
from backend.utils.logger import setup_logger
from backend.api.health import router as health_router
from backend.api.agents import router as agents_router
from backend.api.websocket import router as ws_router
from backend.api.brokers import router as brokers_router
from backend.api.trades import router as trades_router
from backend.api.dashboard import router as dashboard_router
from backend.api.settings_api import router as settings_router
from backend.api.analytics import router as analytics_router
from backend.api.backtest_ui import router as backtest_ui_router
from backend.api.llm_config import router as llm_config_router
from backend.api.room_layouts import router as room_layouts_router
from backend.api.agent_appearance import router as agent_appearance_router
from backend.auth.router import router as auth_router
from backend.notifications.router import router as notifications_router

logger = setup_logger("labourious", settings.LOG_DIR, settings.LOG_LEVEL)

_orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator
    _snapshot_scheduler = None
    _digest_scheduler = None
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db(settings.DATABASE_URL)
    logger.info("Database initialized")

    if settings.JWT_SECRET_KEY == "change-me-in-production-32-chars-min":
        logger.warning("JWT_SECRET_KEY is using insecure default — set JWT_SECRET_KEY env var in production")

    # Start orchestrator if vault password configured
    if settings.VAULT_PASSWORD:
        try:
            from backend.vault.encrypted_vault import EncryptedVault
            from backend.orchestrator.agent_orchestrator import AgentOrchestrator

            vault_path = Path(settings.VAULT_PATH)
            vault = EncryptedVault(vault_path, settings.VAULT_PASSWORD)
            session_factory = get_session_factory(settings.DATABASE_URL)
            _orchestrator = AgentOrchestrator(vault, session_factory)
            await _orchestrator.initialize()
            logger.info("Agent orchestrator started")
        except Exception as e:
            logger.warning(f"Orchestrator startup skipped: {e}")

    # Schedule EOD snapshot job (fires at 16:05 EST = 21:05 UTC)
    try:
        from backend.analytics.snapshot_job import run_eod_snapshot

        _snapshot_scheduler = AsyncIOScheduler()
        _snapshot_scheduler.add_job(
            run_eod_snapshot,
            trigger="cron",
            hour=21,
            minute=5,
            args=[settings.DATABASE_URL],
            id="eod_snapshot",
            replace_existing=True,
        )
        _snapshot_scheduler.start()
        logger.info("EOD snapshot scheduler started (21:05 UTC daily)")
    except Exception as e:
        logger.warning(f"Snapshot scheduler startup skipped: {e}")

    # Daily digest job (fires at 08:00 UTC)
    try:
        from backend.notifications.digest_job import run_daily_digest as _run_digest
        _digest_scheduler = AsyncIOScheduler()
        _digest_scheduler.add_job(
            _run_digest,
            trigger="cron",
            hour=8,
            minute=0,
            args=[settings.DATABASE_URL],
            id="daily_digest",
            replace_existing=True,
        )
        _digest_scheduler.start()
        logger.info("Daily digest scheduler started (08:00 UTC daily)")
    except Exception as e:
        logger.warning(f"Digest scheduler startup skipped: {e}")

    yield

    if _snapshot_scheduler and _snapshot_scheduler.running:
        _snapshot_scheduler.shutdown(wait=False)
    if _digest_scheduler and _digest_scheduler.running:
        _digest_scheduler.shutdown(wait=False)
    if _orchestrator:
        await _orchestrator.shutdown()
        logger.info("Agent orchestrator stopped")
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Trading Warroom — autonomous agent orchestration platform",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=dict(exc.headers) if exc.headers else None,
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(agents_router)
app.include_router(ws_router)
app.include_router(brokers_router)
app.include_router(trades_router)
app.include_router(dashboard_router)
app.include_router(settings_router)
app.include_router(analytics_router)
app.include_router(backtest_ui_router)
app.include_router(llm_config_router)
app.include_router(room_layouts_router)
app.include_router(agent_appearance_router)
app.include_router(auth_router)
app.include_router(notifications_router)

from backend.middleware.error_handler import register_error_handlers
register_error_handlers(app)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
