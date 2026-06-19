import logging
from typing import Optional
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Anthropic Claude API client. API key from vault, never env/DB."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.model = model
        self._client = AsyncAnthropic(api_key=api_key)

    async def generate(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        try:
            msg = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return None
