from backend.trading.confidence_scorer import calculate_confidence_score


def test_base():
    assert calculate_confidence_score() == 10


def test_api_bonus():
    assert calculate_confidence_score(connected_apis=2) == 20


def test_api_capped():
    assert calculate_confidence_score(connected_apis=10) == 40  # 10+30


def test_paid_api():
    assert calculate_confidence_score(paid_apis=1) == 20  # 10+10


def test_context_scores():
    assert calculate_confidence_score(context_detail_score=1) == 20  # 10+10
    assert calculate_confidence_score(context_detail_score=2) == 30  # 10+20


def test_win_bonus():
    assert calculate_confidence_score(wins=10) == 14  # 10 + (10//5)*2 = 10+4


def test_win_capped():
    score = calculate_confidence_score(wins=200)
    assert score == 50  # 10+40


def test_loss_penalty():
    assert calculate_confidence_score(losses=3) == 4  # 10-6


def test_streak_penalty():
    assert calculate_confidence_score(consecutive_losses=3) == 0  # 10-10


def test_auto_pause_penalty():
    assert calculate_confidence_score(auto_paused=True) == 0  # 10-20, clamped


def test_clamp_min():
    assert calculate_confidence_score(losses=100) == 0


def test_clamp_max():
    score = calculate_confidence_score(connected_apis=6, context_detail_score=2, wins=200)
    assert score == 100
