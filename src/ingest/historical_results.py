"""Loads historical international match results from a local CSV cache.

Source: OpenFootball (github.com/openfootball/worldcup.json) and/or any
results CSV the user drops into data/raw/ with columns:
  date, home_team, away_team, home_goals, away_goals, competition[, neutral_venue]

Populating data/raw/ is a one-time manual step (download the public-domain
JSON/CSV dumps) -- this module just standardizes loading + cleaning whatever
is there, it does not fetch from the network itself.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

REQUIRED_COLUMNS = ["date", "home_team", "away_team", "home_goals", "away_goals"]


def load_results_csv(filename: str = "international_results.csv") -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"No historical results file at {path}. Download a results CSV "
            "(e.g. from OpenFootball or Kaggle World Cup datasets) with columns "
            f"{REQUIRED_COLUMNS} and place it there."
        )
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Results CSV is missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"])
    df["home_goals"] = df["home_goals"].astype(int)
    df["away_goals"] = df["away_goals"].astype(int)
    if "neutral_venue" not in df.columns:
        df["neutral_venue"] = False
    if "competition" not in df.columns:
        df["competition"] = "qualifier"
    return df.sort_values("date").reset_index(drop=True)
