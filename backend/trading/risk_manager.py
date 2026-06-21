import logging
from typing import Optional

logger = logging.getLogger(__name__)

CONFIDENCE_MIN = 35   # below this → too risky per AGENTS.md
MAX_CONSECUTIVE_LOSSES = 3


def check_agent_risk(
    agent_id: str,
    confidence_score: int,
    consecutive_losses: int,
    drawdown: Optional[float] = None,
    max_drawdown: Optional[float] = None,
) -> tuple[bool, Optional[str]]:
    """Return (should_pause, reason). None reason means OK.

    Args:
        drawdown: current drawdown as negative float e.g. -0.15
        max_drawdown: limit as negative float e.g. -0.25
    """
    if confidence_score < CONFIDENCE_MIN:
        reason = f"confidence {confidence_score}% < {CONFIDENCE_MIN}%"
        logger.warning(f"agent {agent_id} pause: {reason}")
        return True, reason

    if consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
        reason = f"{consecutive_losses} consecutive losses"
        logger.warning(f"agent {agent_id} pause: {reason}")
        return True, reason

    if drawdown is not None and max_drawdown is not None and drawdown < max_drawdown:
        reason = f"drawdown {drawdown:.1%} < limit {max_drawdown:.1%}"
        logger.warning(f"agent {agent_id} pause: {reason}")
        return True, reason

    return False, None
