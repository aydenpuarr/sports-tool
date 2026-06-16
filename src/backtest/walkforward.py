"""Walk-forward backtest for the Dixon-Coles + Elo blended model.

Avoids lookahead bias: for each match in chronological order, the model is
fit only on matches strictly before that match's date, then used to predict
the outcome. Brier score and RPS (rank probability score -- penaltyblog's
`pb.metrics`) measure calibration, since raw ROI is too noisy on small
historical samples to trust on its own (see plan's backtesting research).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import penaltyblog as pb

from src.models.dixon_coles import ScorelineModel
from src.models.elo import EloRatings
from src.models.blend import blend_probabilities

OUTCOME_HOME, OUTCOME_DRAW, OUTCOME_AWAY = 0, 1, 2


@dataclass
class BacktestResult:
    n_matches: int
    brier_score: float
    rps_mean: float
    predictions: pd.DataFrame  # per-match probabilities + actual outcome


def _actual_outcome(home_goals: int, away_goals: int) -> int:
    if home_goals > away_goals:
        return OUTCOME_HOME
    if home_goals < away_goals:
        return OUTCOME_AWAY
    return OUTCOME_DRAW


def run_walkforward(
    results: pd.DataFrame,
    min_training_matches: int = 200,
    refit_every: int = 50,
    elo_weight: float = 0.3,
) -> BacktestResult:
    """results must be sorted by date ascending with columns: date, home_team,
    away_team, home_goals, away_goals, competition[, neutral_venue].

    Refitting Dixon-Coles after every single match is expensive, so the model
    is refit every `refit_every` matches and reused for predictions in
    between -- a standard walk-forward compromise, not a lookahead violation
    since each refit still only uses strictly-past data.
    """
    results = results.sort_values("date").reset_index(drop=True)

    elo = EloRatings()
    # Warm up Elo on the initial training window so early test predictions
    # aren't starting from flat 1500 ratings for every team.
    for _, row in results.iloc[:min_training_matches].iterrows():
        elo.update_match(
            row["home_team"], row["away_team"], row["home_goals"], row["away_goals"],
            competition=row.get("competition", "qualifier"),
            neutral_venue=bool(row.get("neutral_venue", False)),
        )

    scoreline_model = ScorelineModel()
    rows = []

    for i in range(min_training_matches, len(results)):
        if (i - min_training_matches) % refit_every == 0:
            train = results.iloc[:i]
            scoreline_model.fit(train)

        row = results.iloc[i]
        home, away = row["home_team"], row["away_team"]
        neutral = bool(row.get("neutral_venue", False))

        try:
            dc = scoreline_model.predict(home, away, neutral_venue=neutral)
        except Exception:
            # Unseen team in this training window (e.g. first World Cup
            # appearance) -- skip, can't price a team with no history yet.
            elo.update_match(home, away, row["home_goals"], row["away_goals"],
                              competition=row.get("competition", "qualifier"), neutral_venue=neutral)
            continue

        elo_probs = elo.win_draw_loss_probabilities(home, away, neutral_venue=neutral)
        home_p, draw_p, away_p = blend_probabilities(dc, elo_probs, elo_weight=elo_weight)

        actual = _actual_outcome(row["home_goals"], row["away_goals"])
        rows.append({
            "date": row["date"], "home_team": home, "away_team": away,
            "home_win_prob": home_p, "draw_prob": draw_p, "away_win_prob": away_p,
            "actual_outcome": actual,
        })

        elo.update_match(home, away, row["home_goals"], row["away_goals"],
                          competition=row.get("competition", "qualifier"), neutral_venue=neutral)

    pred_df = pd.DataFrame(rows)
    if pred_df.empty:
        return BacktestResult(0, float("nan"), float("nan"), pred_df)

    prob_matrix = pred_df[["home_win_prob", "draw_prob", "away_win_prob"]].to_numpy()
    outcomes = pred_df["actual_outcome"].to_numpy()

    brier = pb.metrics.briar.multiclass_brier_score(prob_matrix, outcomes)
    rps_values = pb.metrics.rps.rps_array(prob_matrix, outcomes)
    rps_mean = float(np.mean(rps_values))

    return BacktestResult(
        n_matches=len(pred_df), brier_score=float(brier), rps_mean=rps_mean, predictions=pred_df
    )
