import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class OllamaClient:
    """Local Ollama LLM via HTTP."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self.base_url = base_url
        self.model = model
        self._client = httpx.AsyncClient(timeout=30.0)

    async def generate(self, prompt: str) -> Optional[str]:
        try:
            resp = await self._client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except httpx.ConnectError:
            logger.error(f"Ollama unreachable at {self.base_url}")
            return None
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return None

    async def close(self):
        await self._client.aclose()
