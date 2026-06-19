from backend.trading.risk_manager import check_agent_risk


def test_ok():
    paused, reason = check_agent_risk("a1", confidence_score=50, consecutive_losses=0)
    assert not paused
    assert reason is None


def test_low_confidence():
    paused, reason = check_agent_risk("a1", confidence_score=29, consecutive_losses=0)
    assert paused
    assert "confidence" in reason


def test_confidence_at_boundary():
    paused, _ = check_agent_risk("a1", confidence_score=30, consecutive_losses=0)
    assert not paused


def test_consecutive_losses():
    paused, reason = check_agent_risk("a1", confidence_score=50, consecutive_losses=3)
    assert paused
    assert "consecutive" in reason


def test_drawdown_ok():
    paused, _ = check_agent_risk("a1", 50, 0, drawdown=-0.10, max_drawdown=-0.25)
    assert not paused


def test_drawdown_breach():
    paused, reason = check_agent_risk("a1", 50, 0, drawdown=-0.30, max_drawdown=-0.25)
    assert paused
    assert "drawdown" in reason


def test_confidence_checked_first():
    # even with drawdown breach, confidence triggers first
    paused, reason = check_agent_risk("a1", 10, 0, drawdown=-0.50, max_drawdown=-0.25)
    assert "confidence" in reason
