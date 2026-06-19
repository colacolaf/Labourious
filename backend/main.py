from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

logger = setup_logger("labourious", settings.LOG_DIR, settings.LOG_LEVEL)

_orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db(settings.DATABASE_URL)
    logger.info("Database initialized")

    # Start orchestrator if vault password configured
    if settings.VAULT_PASSWORD:
        try:
            from backend.vault.encrypted_vault import EncryptedVault
            from backend.orchestrator.agent_orchestrator import AgentOrchestrator

            vault = EncryptedVault(settings.VAULT_PASSWORD)
            session_factory = get_session_factory(settings.DATABASE_URL)
            _orchestrator = AgentOrchestrator(vault, session_factory)
            await _orchestrator.initialize()
            logger.info("Agent orchestrator started")
        except Exception as e:
            logger.warning(f"Orchestrator startup skipped: {e}")

    yield

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
