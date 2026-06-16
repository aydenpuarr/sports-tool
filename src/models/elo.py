"""National-team Elo ratings, following eloratings.net's published methodology.

K factor depends on competition importance:
  60 - World Cup finals
  50 - continental championship / Confederations Cup
  40 - World Cup / continental qualifiers
  30 - other tournaments
  20 - friendlies

Expected result uses the standard logistic Elo curve. Goal difference scales
the result multiplier (a multi-goal win counts for more than a 1-0). Home
advantage is a fixed rating-point bonus added before computing the expected
result.
"""
from __future__ import annotations

from dataclasses import dataclass, field

K_FACTORS = {
    "world_cup_final": 60,
    "continental_final": 50,
    "qualifier": 40,
    "other_tournament": 30,
    "friendly": 20,
}

DEFAULT_RATING = 1500.0
HOME_ADVANTAGE = 100.0


def goal_diff_multiplier(goal_diff: int) -> float:
    """eloratings.net's goal-difference scaling for the K factor."""
    gd = abs(goal_diff)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** (-(rating_a - rating_b) / 400.0))


@dataclass
class EloRatings:
    ratings: dict[str, float] = field(default_factory=dict)

    def get(self, team: str) -> float:
        return self.ratings.get(team, DEFAULT_RATING)

    def update_match(
        self,
        home: str,
        away: str,
        home_goals: int,
        away_goals: int,
        competition: str = "qualifier",
        neutral_venue: bool = False,
    ) -> None:
        k = K_FACTORS.get(competition, K_FACTORS["qualifier"])
        r_home = self.get(home)
        r_away = self.get(away)

        adj_home = r_home + (0.0 if neutral_venue else HOME_ADVANTAGE)

        if home_goals > away_goals:
            actual_home = 1.0
        elif home_goals < away_goals:
            actual_home = 0.0
        else:
            actual_home = 0.5

        expected_home = expected_score(adj_home, r_away)
        multiplier = goal_diff_multiplier(home_goals - away_goals)
        delta = k * multiplier * (actual_home - expected_home)

        self.ratings[home] = r_home + delta
        self.ratings[away] = r_away - delta

    def win_draw_loss_probabilities(
        self, home: str, away: str, neutral_venue: bool = False
    ) -> tuple[float, float, float]:
        """Rough Elo-only win/draw/loss split (Dixon-Coles refines this further)."""
        r_home = self.get(home) + (0.0 if neutral_venue else HOME_ADVANTAGE)
        r_away = self.get(away)
        p_home_or_draw_split = expected_score(r_home, r_away)

        # Heuristic draw probability shrinking as the rating gap grows.
        gap = abs(r_home - r_away)
        draw_prob = max(0.18, 0.30 - gap / 2000.0)
        win_prob_total = 1.0 - draw_prob
        home_win = win_prob_total * p_home_or_draw_split
        away_win = win_prob_total * (1.0 - p_home_or_draw_split)
        return home_win, draw_prob, away_win
