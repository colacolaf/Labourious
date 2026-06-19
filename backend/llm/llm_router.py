import json
import logging
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from backend.llm.ollama_client import OllamaClient
from backend.llm.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


class TradeDecision(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(ge=0.0, le=1.0)
    position_size: float = Field(ge=0.0, le=1.0)
    stop_loss: float = Field(default=-0.05)
    take_profit: float = Field(default=0.15)
    reasoning: str = ""


_HOLD = TradeDecision(action="HOLD", confidence=0.0, position_size=0.0, reasoning="fallback")

_JSON_RE = re.compile(r'\{[^{}]*\}', re.DOTALL)

_PROMPT_TEMPLATE = """\
You are a trading AI. Decide BUY, SELL, or HOLD based on the rules and data below.

TRADING RULES:
{context}

MARKET DATA:
- Symbol: {symbol}
- Price: ${price:.2f}
- Volume: {volume:.0f}
- RSI(14): {rsi}
- MA20: ${ma20:.2f}
- MA50: ${ma50:.2f}

Respond ONLY with raw JSON, no markdown:
{{"action":"BUY|SELL|HOLD","confidence":0.0-1.0,"position_size":0.0-1.0,"stop_loss":-0.05,"take_profit":0.15,"reasoning":"brief"}}
"""


def _parse(text: str) -> Optional[TradeDecision]:
    """Try raw JSON, then regex-extracted JSON."""
    for candidate in [text, *_JSON_RE.findall(text)]:
        try:
            return TradeDecision.model_validate(json.loads(candidate))
        except (json.JSONDecodeError, ValidationError):
            continue
    return None


class LLMRouter:
    def __init__(
        self,
        use_local: bool = True,
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "mistral",
        claude_api_key: Optional[str] = None,
        claude_model: str = "claude-sonnet-4-6",
    ):
        self.use_local = use_local
        self._ollama = OllamaClient(base_url=ollama_url, model=ollama_model) if use_local else None
        self._claude = (
            ClaudeClient(api_key=claude_api_key, model=claude_model)
            if not use_local and claude_api_key
            else None
        )

    def build_prompt(self, symbol: str, market_data: dict, context: str) -> str:
        return _PROMPT_TEMPLATE.format(
            context=context,
            symbol=symbol,
            price=float(market_data.get("price", 0)),
            volume=float(market_data.get("volume", 0)),
            rsi=market_data.get("rsi", "N/A"),
            ma20=float(market_data.get("ma20", 0)),
            ma50=float(market_data.get("ma50", 0)),
        )

    async def decide(
        self,
        symbol: str,
        market_data: dict,
        context: str,
        max_retries: int = 3,
    ) -> TradeDecision:
        prompt = self.build_prompt(symbol, market_data, context)

        for attempt in range(max_retries):
            try:
                if self.use_local and self._ollama:
                    raw = await self._ollama.generate(prompt)
                elif self._claude:
                    raw = await self._claude.generate(prompt)
                else:
                    logger.error("no LLM configured")
                    return _HOLD

                if not raw:
                    logger.warning(f"empty LLM response (attempt {attempt + 1})")
                else:
                    decision = _parse(raw)
                    if decision:
                        logger.info(f"LLM → {decision.action} conf={decision.confidence:.0%}")
                        return decision
                    logger.warning(f"parse failed (attempt {attempt + 1}): {raw[:80]}")

                # append clarification for next attempt
                prompt += "\n\nPrevious response invalid. Reply ONLY with raw JSON."
            except Exception as e:
                logger.error(f"LLM error attempt {attempt + 1}: {e}")

        logger.warning(f"all {max_retries} attempts failed → HOLD")
        return _HOLD
