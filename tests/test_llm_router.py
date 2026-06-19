import pytest
from unittest.mock import AsyncMock, patch

from backend.llm.llm_router import LLMRouter, TradeDecision, _parse

_VALID_JSON = '{"action":"BUY","confidence":0.75,"position_size":0.05,"stop_loss":-0.05,"take_profit":0.15,"reasoning":"rsi low"}'
_WRAPPED = f"```json\n{_VALID_JSON}\n```"
_BAD = "I think you should BUY but I cannot give JSON"


def test_parse_raw():
    d = _parse(_VALID_JSON)
    assert d is not None
    assert d.action == "BUY"


def test_parse_markdown_wrapped():
    d = _parse(_WRAPPED)
    assert d is not None
    assert d.action == "BUY"


def test_parse_invalid():
    assert _parse("nope") is None


def test_build_prompt_contains_symbol():
    router = LLMRouter(use_local=True)
    prompt = router.build_prompt("AAPL", {"price": 150, "volume": 1e6, "rsi": 28, "ma20": 152, "ma50": 155}, "rules")
    assert "AAPL" in prompt
    assert "RSI" in prompt


@pytest.mark.asyncio
async def test_decide_success():
    router = LLMRouter(use_local=True)
    router._ollama = AsyncMock()
    router._ollama.generate = AsyncMock(return_value=_VALID_JSON)

    d = await router.decide("AAPL", {"price": 150, "volume": 0, "rsi": 28, "ma20": 0, "ma50": 0}, "rules")
    assert d.action == "BUY"
    assert d.confidence == 0.75


@pytest.mark.asyncio
async def test_decide_retry_then_succeed():
    router = LLMRouter(use_local=True)
    router._ollama = AsyncMock()
    router._ollama.generate = AsyncMock(side_effect=[_BAD, _VALID_JSON])

    d = await router.decide("X", {}, "rules", max_retries=3)
    assert d.action == "BUY"
    assert router._ollama.generate.call_count == 2


@pytest.mark.asyncio
async def test_decide_all_fail_returns_hold():
    router = LLMRouter(use_local=True)
    router._ollama = AsyncMock()
    router._ollama.generate = AsyncMock(return_value=_BAD)

    d = await router.decide("X", {}, "rules", max_retries=2)
    assert d.action == "HOLD"
    assert d.confidence == 0.0


@pytest.mark.asyncio
async def test_decide_no_llm_returns_hold():
    router = LLMRouter(use_local=True)
    router._ollama = None

    d = await router.decide("X", {}, "rules")
    assert d.action == "HOLD"
