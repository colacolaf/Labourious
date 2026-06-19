from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.config import settings as app_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class LLMSettings(BaseModel):
    use_local_llm: bool = True
    ollama_model: Optional[str] = "mistral"
    ollama_base_url: Optional[str] = "http://localhost:11434"


class AllocationSettings(BaseModel):
    max_portfolio_drawdown: float = 0.25
    default_position_size: float = 0.05
    max_agents: int = 20


# ponytail: in-memory settings store; persist to .env file when needed
_llm_settings = LLMSettings()
_allocation_settings = AllocationSettings()


@router.get("")
async def get_settings():
    """Get current app settings (non-sensitive)."""
    return {
        "llm": _llm_settings.model_dump(),
        "allocation": _allocation_settings.model_dump(),
        "app": {
            "debug": app_settings.DEBUG,
            "version": app_settings.APP_VERSION,
            "ws_heartbeat_interval": app_settings.WS_HEARTBEAT_INTERVAL,
        },
    }


@router.post("/llm")
async def update_llm_settings(data: LLMSettings):
    """Update LLM routing settings."""
    global _llm_settings
    _llm_settings = data
    return {"status": "updated", "llm": _llm_settings.model_dump()}


@router.post("/allocation")
async def update_allocation_settings(data: AllocationSettings):
    """Update portfolio allocation settings."""
    global _allocation_settings
    _allocation_settings = data
    return {"status": "updated", "allocation": _allocation_settings.model_dump()}
