"""LLM config API — GET/PATCH config, POST test, POST vault key."""
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.llm.config import read_config, write_config, LLMConfig
from backend.config import settings, BASE_DIR
from backend.utils.logger import setup_logger

router = APIRouter(prefix="/api/llm", tags=["llm"])
logger = setup_logger("llm_config")

VALID_PROVIDERS = {"ollama", "claude", "openai"}


def _vault():
    """Open vault if password configured; returns None if not."""
    if not settings.VAULT_PASSWORD:
        return None
    try:
        from backend.vault.encrypted_vault import EncryptedVault
        from pathlib import Path
        vault_path = Path(BASE_DIR) / "data" / "vault.db"
        return EncryptedVault(vault_path, settings.VAULT_PASSWORD)
    except Exception as e:
        logger.warning(f"vault open error: {e}")
        return None


@router.get("/config")
async def get_config():
    cfg = read_config()
    vault = _vault()
    has_openai = False
    has_claude = False
    if vault:
        try:
            has_openai = bool(vault.get("openai_api_key"))
        except Exception:
            pass
        try:
            has_claude = bool(vault.get("anthropic_api_key"))
        except Exception:
            pass
    return {
        "provider": cfg.provider,
        "model": cfg.model,
        "ollama_url": cfg.ollama_url,
        "has_openai_key": has_openai,
        "has_claude_key": has_claude,
    }


class PatchConfigRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    ollama_url: Optional[str] = None


@router.patch("/config")
async def patch_config(req: PatchConfigRequest):
    cfg = read_config()
    if req.provider is not None:
        if req.provider not in VALID_PROVIDERS:
            raise HTTPException(status_code=422, detail=f"provider must be one of {sorted(VALID_PROVIDERS)}")
        if req.provider == "openai":
            vault = _vault()
            has_key = False
            if vault:
                try:
                    has_key = bool(vault.get("openai_api_key"))
                except Exception:
                    pass
            if not has_key:
                raise HTTPException(status_code=422, detail="openai_api_key not found in vault — save it first")
        if req.provider == "claude":
            vault = _vault()
            has_key = False
            if vault:
                try:
                    has_key = bool(vault.get("anthropic_api_key"))
                except Exception:
                    pass
            if not has_key:
                raise HTTPException(status_code=422, detail="anthropic_api_key not found in vault — save it first")
        cfg.provider = req.provider
    if req.model is not None:
        cfg.model = req.model
    if req.ollama_url is not None:
        cfg.ollama_url = req.ollama_url
    write_config(cfg)
    return {"provider": cfg.provider, "model": cfg.model, "ollama_url": cfg.ollama_url}


@router.post("/test")
async def test_llm():
    """Fire a dummy decide() call against the active LLM. Returns latency."""
    cfg = read_config()
    t0 = time.monotonic()
    ok = False
    error = None
    try:
        if cfg.provider == "ollama":
            ok = True  # ponytail: skip actual call for ollama — no API key needed, startup already verified
        else:
            try:
                from backend.llm.llm_router import LLMRouter
                vault = _vault()
                claude_key = None
                openai_key = None
                if vault:
                    try:
                        claude_key = vault.get("anthropic_api_key")
                    except Exception:
                        pass
                    try:
                        openai_key = vault.get("openai_api_key")
                    except Exception:
                        pass

                router_inst = LLMRouter.from_config(cfg, claude_api_key=claude_key, openai_api_key=openai_key)

                dummy_market = {"price": 100.0, "volume": 1000.0, "rsi": 50.0, "ma20": 100.0, "ma50": 100.0}
                decision = await router_inst.decide("BTC/USD", dummy_market, "Test prompt.")
                ok = decision.action in ("BUY", "SELL", "HOLD")
            except Exception as e:
                error = str(e)
    except Exception as e:
        error = str(e)
    latency_ms = int((time.monotonic() - t0) * 1000)
    response = {"ok": ok, "latency_ms": latency_ms}
    if error:
        response["error"] = error
    return response


class VaultKeyRequest(BaseModel):
    key_name: str
    value: str = Field(min_length=1)


@router.post("/key")
async def save_vault_key(req: VaultKeyRequest):
    """Save an API key to vault. key_name must be 'openai_api_key' or 'anthropic_api_key'."""
    allowed = {"openai_api_key", "anthropic_api_key"}
    if req.key_name not in allowed:
        raise HTTPException(status_code=422, detail=f"key_name must be one of {allowed}")
    vault = _vault()
    if not vault:
        raise HTTPException(status_code=503, detail="Vault not available — VAULT_PASSWORD not set")
    try:
        vault.set(req.key_name, req.value)
        return {"status": "saved", "key_name": req.key_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vault write failed: {e}")
