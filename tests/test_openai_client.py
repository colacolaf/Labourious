import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.llm.openai_client import OpenAIClient


@pytest.fixture
def client():
    return OpenAIClient(api_key="sk-test-fake", model="gpt-4o")


@pytest.mark.asyncio
async def test_generate_returns_text(client):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"action":"HOLD","confidence":0.5,"position_size":0.0,"reasoning":"test"}'

    with patch.object(client._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)):
        result = await client.generate("test prompt")

    assert result is not None
    assert "HOLD" in result


@pytest.mark.asyncio
async def test_generate_returns_none_on_exception(client):
    with patch.object(client._client.chat.completions, "create", new=AsyncMock(side_effect=Exception("API error"))):
        result = await client.generate("test prompt")

    assert result is None


@pytest.mark.asyncio
async def test_generate_returns_none_on_timeout(client):
    import asyncio
    with patch.object(client._client.chat.completions, "create", new=AsyncMock(side_effect=asyncio.TimeoutError())):
        result = await client.generate("test prompt")

    assert result is None


@pytest.mark.asyncio
async def test_generate_passes_correct_model(client):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "response"

    with patch.object(client._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)) as mock_create:
        await client.generate("prompt")
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["max_tokens"] == 500
