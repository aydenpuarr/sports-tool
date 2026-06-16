import pytest

from src.odds.value import evaluate_bet, implied_probability, kelly_fraction, BetTier


def test_implied_probability():
    assert abs(implied_probability(2.0) - 0.5) < 1e-9
    assert abs(implied_probability(4.0) - 0.25) < 1e-9


def test_implied_probability_rejects_invalid_odds():
    with pytest.raises(ValueError):
        implied_probability(1.0)


def test_kelly_fraction_zero_when_no_edge():
    # Model probability exactly matches the implied probability -> no edge.
    assert kelly_fraction(0.5, 2.0) == pytest.approx(0.0, abs=1e-9)


def test_kelly_fraction_positive_with_edge():
    # Model thinks 60% but bookmaker odds imply only 50% -> positive edge.
    f = kelly_fraction(0.6, 2.0)
    assert f > 0


def test_safe_tier_for_high_probability_low_odds_with_edge():
    # implied probability at 1.6 is 62.5%, below the model's 75% -> positive edge.
    evaluation = evaluate_bet("home_win", model_probability=0.75, decimal_odds=1.6)
    assert evaluation.tier == BetTier.SAFE


def test_value_tier_for_lower_probability_with_edge():
    # implied probability at 4.5 is ~22%, model thinks 30% -> clear positive edge.
    evaluation = evaluate_bet("away_win", model_probability=0.30, decimal_odds=4.5)
    assert evaluation.tier == BetTier.VALUE


def test_no_bet_tier_when_bookmaker_overprices_outcome():
    evaluation = evaluate_bet("draw", model_probability=0.20, decimal_odds=2.0)
    assert evaluation.tier == BetTier.NO_BET
