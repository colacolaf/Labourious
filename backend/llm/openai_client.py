import logging
from typing import Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIClient:
    """OpenAI GPT-4o async client. API key from vault, never env/DB."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, timeout=30.0)

    async def generate(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return None
