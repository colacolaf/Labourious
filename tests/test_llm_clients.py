import pytest
import respx
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from backend.llm.ollama_client import OllamaClient
from backend.llm.claude_client import ClaudeClient


@pytest.mark.asyncio
@respx.mock
async def test_ollama_generate():
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "HOLD"})
    )
    client = OllamaClient()
    result = await client.generate("test")
    assert result == "HOLD"


@pytest.mark.asyncio
@respx.mock
async def test_ollama_connect_error():
    respx.post("http://localhost:11434/api/generate").mock(
        side_effect=httpx.ConnectError("refused")
    )
    client = OllamaClient()
    result = await client.generate("test")
    assert result is None


@pytest.mark.asyncio
async def test_claude_generate():
    with patch("backend.llm.claude_client.AsyncAnthropic") as mock_cls:
        mock_inst = AsyncMock()
        mock_inst.messages.create = AsyncMock(
            return_value=MagicMock(content=[MagicMock(text="BUY")])
        )
        mock_cls.return_value = mock_inst
        client = ClaudeClient(api_key="test")
        result = await client.generate("prompt")
        assert result == "BUY"


@pytest.mark.asyncio
async def test_claude_error_returns_none():
    with patch("backend.llm.claude_client.AsyncAnthropic") as mock_cls:
        mock_inst = AsyncMock()
        mock_inst.messages.create = AsyncMock(side_effect=Exception("rate limit"))
        mock_cls.return_value = mock_inst
        client = ClaudeClient(api_key="test")
        result = await client.generate("prompt")
        assert result is None
