import logging

logger = logging.getLogger(__name__)


def calculate_confidence_score(
    connected_apis: int = 0,
    paid_apis: int = 0,
    context_detail_score: int = 0,  # 0=none, 1=improved, 2=detailed
    wins: int = 0,
    losses: int = 0,
    consecutive_losses: int = 0,
    auto_paused: bool = False,
) -> int:
    """Confidence score 0-100 per AGENTS.md formula.

    Base 10 + API_Score (0-30) + Performance_Score (0-40) + Context_Score (0-20)
    """
    # API score: +5 per free API, +10 per paid (cap 30)
    api_score = min(30, connected_apis * 5 + paid_apis * 10)

    # Context score: +5 improved, +10 detailed (cap 20)
    context_score = min(20, context_detail_score * 10)

    # Performance score: +2 per 5 consecutive wins (cap 40)
    performance_score = min(40, (wins // 5) * 2)

    # Penalties
    loss_penalty = losses * 2
    streak_penalty = 10 if consecutive_losses >= 3 else 0
    pause_penalty = 20 if auto_paused else 0

    score = 10 + api_score + context_score + performance_score - loss_penalty - streak_penalty - pause_penalty

    result = max(0, min(100, score))
    logger.debug(
        f"confidence: base=10 api={api_score} ctx={context_score} perf={performance_score} "
        f"penalties={loss_penalty + streak_penalty + pause_penalty} → {result}"
    )
    return result
