"""Compares model probabilities against user-entered bookmaker odds to find
value, and suggests a fractional-Kelly stake. Odds are decimal format
(e.g. 2.50), entered manually by the user from bet365 or any other book --
this tool never scrapes or auto-places bets.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BetTier(Enum):
    SAFE = "safe"
    VALUE = "value"  # higher-odds, positive-edge "risky" pick
    NO_BET = "no_bet"


@dataclass
class BetEvaluation:
    market: str
    model_probability: float
    decimal_odds: float
    implied_probability: float
    edge: float  # model_probability - implied_probability
    kelly_fraction: float  # full Kelly stake as a fraction of bankroll
    suggested_stake_fraction: float  # fractional Kelly actually recommended
    tier: BetTier


def implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("decimal_odds must be > 1.0")
    return 1.0 / decimal_odds


def kelly_fraction(model_probability: float, decimal_odds: float) -> float:
    """f* = (bp - q) / b, where b = net decimal odds, p = win prob, q = 1-p."""
    b = decimal_odds - 1.0
    p = model_probability
    q = 1.0 - p
    if b <= 0:
        return 0.0
    f = (b * p - q) / b
    return max(0.0, f)


def evaluate_bet(
    market: str,
    model_probability: float,
    decimal_odds: float,
    kelly_divisor: float = 4.0,
    safe_probability_threshold: float = 0.60,
    safe_max_odds: float = 1.8,
    min_value_edge: float = 0.05,
) -> BetEvaluation:
    implied = implied_probability(decimal_odds)
    edge = model_probability - implied
    full_kelly = kelly_fraction(model_probability, decimal_odds)
    suggested = full_kelly / kelly_divisor

    if model_probability >= safe_probability_threshold and decimal_odds <= safe_max_odds and edge > 0:
        tier = BetTier.SAFE
    elif edge >= min_value_edge:
        tier = BetTier.VALUE
    else:
        tier = BetTier.NO_BET

    return BetEvaluation(
        market=market,
        model_probability=model_probability,
        decimal_odds=decimal_odds,
        implied_probability=implied,
        edge=edge,
        kelly_fraction=full_kelly,
        suggested_stake_fraction=suggested,
        tier=tier,
    )
