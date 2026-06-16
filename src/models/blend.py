"""Combines Elo, Dixon-Coles, and feature adjustments into one match view.

Dixon-Coles (fit on historical scorelines) is the primary source for market
probabilities (1X2, BTTS, O/U, correct score) since it models the full
scoreline distribution. Elo is used as a sanity cross-check / blend weight
on the 1X2 split, and squad/weather multipliers nudge the attack rates
before the scoreline grid is read off, rather than overriding the
statistical model outright.
"""
from __future__ import annotations

from dataclasses import dataclass

from .dixon_coles import MatchProbabilities, ScorelineModel
from .elo import EloRatings
from .features import Player, combined_attack_multiplier


@dataclass
class MatchView:
    home_team: str
    away_team: str
    dixon_coles: MatchProbabilities
    elo_home_win: float
    elo_draw: float
    elo_away_win: float
    blended_home_win: float
    blended_draw: float
    blended_away_win: float
    home_attack_multiplier: float
    away_attack_multiplier: float


def blend_probabilities(
    dc: MatchProbabilities, elo_probs: tuple[float, float, float], elo_weight: float = 0.3
) -> tuple[float, float, float]:
    """Weighted average of Dixon-Coles and Elo win/draw/loss splits, renormalized."""
    dc_weight = 1.0 - elo_weight
    home = dc.home_win * dc_weight + elo_probs[0] * elo_weight
    draw = dc.draw * dc_weight + elo_probs[1] * elo_weight
    away = dc.away_win * dc_weight + elo_probs[2] * elo_weight
    total = home + draw + away
    return home / total, draw / total, away / total


def _apply_attack_multipliers(
    probs: tuple[float, float, float], home_mult: float, away_mult: float
) -> tuple[float, float, float]:
    """Tilts the home/away win probabilities by the ratio of chemistry/form/
    weather attack multipliers, leaving draw probability untouched before
    renormalizing. A lightweight proxy for full grid re-fitting per match."""
    home, draw, away = probs
    home *= home_mult
    away *= away_mult
    total = home + draw + away
    return home / total, draw / total, away / total


def build_match_view(
    home_team: str,
    away_team: str,
    scoreline_model: ScorelineModel,
    elo_ratings: EloRatings,
    home_squad: list[Player] | None = None,
    away_squad: list[Player] | None = None,
    temperature_c: float = 20.0,
    humidity_pct: float = 50.0,
    home_high_press: bool = False,
    away_high_press: bool = False,
    neutral_venue: bool = True,
    elo_weight: float = 0.3,
) -> MatchView:
    home_mult = (
        combined_attack_multiplier(home_squad, temperature_c, humidity_pct, home_high_press)
        if home_squad
        else 1.0
    )
    away_mult = (
        combined_attack_multiplier(away_squad, temperature_c, humidity_pct, away_high_press)
        if away_squad
        else 1.0
    )
    dc = scoreline_model.predict(home_team, away_team, neutral_venue=neutral_venue)
    elo_probs = elo_ratings.win_draw_loss_probabilities(home_team, away_team, neutral_venue=neutral_venue)

    blended = blend_probabilities(dc, elo_probs, elo_weight=elo_weight)
    blended = _apply_attack_multipliers(blended, home_mult, away_mult)

    return MatchView(
        home_team=home_team,
        away_team=away_team,
        dixon_coles=dc,
        elo_home_win=elo_probs[0],
        elo_draw=elo_probs[1],
        elo_away_win=elo_probs[2],
        blended_home_win=blended[0],
        blended_draw=blended[1],
        blended_away_win=blended[2],
        home_attack_multiplier=home_mult,
        away_attack_multiplier=away_mult,
    )
