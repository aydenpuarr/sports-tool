"""Scoreline probability model wrapping penaltyblog's Dixon-Coles implementation.

Dixon-Coles refines plain independent-Poisson scorelines with a low-score
correlation term (rho) so it stops under-predicting draws like 0-0/1-1, and
optionally exponential time-decay so recent matches count more.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from penaltyblog.models import DixonColesGoalModel


@dataclass
class MatchProbabilities:
    home_win: float
    draw: float
    away_win: float
    btts_yes: float
    over_2_5: float
    correct_score: dict[tuple[int, int], float]
    top_scorelines: list[tuple[tuple[int, int], float]]


class ScorelineModel:
    """Fits a Dixon-Coles model on historical results and prices markets."""

    def __init__(self, max_goals: int = 10, score_grid_size: int = 6):
        self.max_goals = max_goals
        self.score_grid_size = score_grid_size
        self._model: DixonColesGoalModel | None = None

    def fit(self, results: pd.DataFrame) -> None:
        """results needs columns: home_team, away_team, home_goals, away_goals[, date, neutral_venue]."""
        weights = None
        if "date" in results.columns:
            days_ago = (results["date"].max() - results["date"]).dt.days
            half_life_days = 365  # matches a year old count half as much
            weights = (0.5 ** (days_ago / half_life_days)).to_numpy(dtype=np.float64, copy=True)

        neutral = (
            results["neutral_venue"].to_numpy(dtype=bool, copy=True)
            if "neutral_venue" in results.columns
            else None
        )

        self._model = DixonColesGoalModel(
            results["home_goals"].to_numpy(dtype=np.int64, copy=True),
            results["away_goals"].to_numpy(dtype=np.int64, copy=True),
            results["home_team"].to_numpy(copy=True),
            results["away_team"].to_numpy(copy=True),
            weights=weights,
            neutral_venue=neutral,
        )
        self._model.fit()

    def predict(self, home_team: str, away_team: str, neutral_venue: bool = False) -> MatchProbabilities:
        if self._model is None:
            raise RuntimeError("Call fit() before predict().")

        grid = self._model.predict(
            home_team, away_team, max_goals=self.max_goals, neutral_venue=neutral_venue
        )

        n = self.score_grid_size
        correct_score = {(h, a): grid.exact_score(h, a) for h in range(n) for a in range(n)}
        top_scorelines = sorted(correct_score.items(), key=lambda kv: kv[1], reverse=True)[:5]

        return MatchProbabilities(
            home_win=grid.home_win,
            draw=grid.draw,
            away_win=grid.away_win,
            btts_yes=grid.btts_yes,
            over_2_5=grid.total_goals("over", 2.5),
            correct_score=correct_score,
            top_scorelines=top_scorelines,
        )
