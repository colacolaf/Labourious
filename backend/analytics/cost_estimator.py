# Price per input token (update per model release)
_PRICES: dict[str, dict[str, float]] = {
    "claude": {"claude-sonnet-4-6": 3.0 / 1_000_000},
    "openai": {"gpt-4o": 5.0 / 1_000_000},
}
_TOKENS_PER_CALL = 800  # prompt ~600 + response ~200


def estimate_monthly_cost(provider: str, model: str, check_frequency_seconds: int) -> float:
    """Returns estimated $/month. Returns 0.0 for Ollama, zero frequency, or unknown model."""
    if provider == "ollama" or check_frequency_seconds <= 0:
        return 0.0
    price_map = _PRICES.get(provider)
    if not price_map:
        return 0.0
    price = price_map.get(model, 0.0)
    if price == 0.0:
        return 0.0
    calls_per_month = (86400 / check_frequency_seconds) * 30
    return round(_TOKENS_PER_CALL * calls_per_month * price, 2)
