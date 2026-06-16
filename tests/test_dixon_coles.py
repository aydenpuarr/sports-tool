import numpy as np
import pandas as pd
import pytest

from src.models.dixon_coles import ScorelineModel


@pytest.fixture
def synthetic_results():
    rng = np.random.default_rng(0)
    teams = ["Brazil", "Argentina", "France", "Germany", "Spain", "England"]
    rows = []
    base = pd.Timestamp("2020-01-01")
    for i in range(300):
        h, a = rng.choice(teams, 2, replace=False)
        rows.append({
            "date": base + pd.Timedelta(days=i),
            "home_team": h, "away_team": a,
            "home_goals": rng.poisson(1.5), "away_goals": rng.poisson(1.1),
        })
    return pd.DataFrame(rows)


def test_fit_requires_call_before_predict():
    model = ScorelineModel()
    with pytest.raises(RuntimeError):
        model.predict("Brazil", "Argentina")


def test_probabilities_sum_to_one(synthetic_results):
    model = ScorelineModel()
    model.fit(synthetic_results)
    probs = model.predict("Brazil", "Argentina")
    total = probs.home_win + probs.draw + probs.away_win
    assert abs(total - 1.0) < 1e-6


def test_correct_score_grid_sums_less_than_or_equal_to_one(synthetic_results):
    model = ScorelineModel()
    model.fit(synthetic_results)
    probs = model.predict("Brazil", "Argentina")
    assert sum(probs.correct_score.values()) <= 1.0 + 1e-6


def test_top_scorelines_sorted_descending(synthetic_results):
    model = ScorelineModel()
    model.fit(synthetic_results)
    probs = model.predict("Brazil", "Argentina")
    probabilities = [p for _, p in probs.top_scorelines]
    assert probabilities == sorted(probabilities, reverse=True)
