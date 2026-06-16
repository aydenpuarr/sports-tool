"""Downloads and caches OpenFootball World Cup fixtures/results (public domain,
no API key, no rate limits) -- both historical editions for model training and
the live 2026 tournament for current predictions.

Run this script directly to populate data/raw/:
    python3 -m src.ingest.openfootball
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
BASE_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master"

HISTORICAL_YEARS = [2006, 2010, 2014, 2018, 2022]
CURRENT_YEAR = 2026


def _fetch_json(year: int) -> dict:
    url = f"{BASE_URL}/{year}/worldcup.json"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())


def _parse_matches(data: dict, year: int, is_wc: bool = True) -> list[dict]:
    rows = []
    for match in data.get("matches", []):
        score = match.get("score", {})
        ft = score.get("ft")
        if not ft or len(ft) < 2:
            # Upcoming / no result yet
            home_goals = away_goals = None
        else:
            home_goals, away_goals = ft[0], ft[1]

        round_name = match.get("round", "")
        is_final = "final" in round_name.lower()
        competition = "world_cup_final" if is_final else ("qualifier" if not is_wc else "world_cup_final")

        rows.append({
            "date": match.get("date"),
            "home_team": match.get("team1"),
            "away_team": match.get("team2"),
            "home_goals": home_goals,
            "away_goals": away_goals,
            "competition": competition,
            "neutral_venue": True,
            "year": year,
            "round": round_name,
            "venue": match.get("ground", {}).get("name", "") if isinstance(match.get("ground"), dict) else str(match.get("ground", "")),
        })
    return rows


def download_historical(years: list[int] = HISTORICAL_YEARS) -> pd.DataFrame:
    all_rows = []
    for year in years:
        try:
            data = _fetch_json(year)
            rows = _parse_matches(data, year)
            all_rows.extend(rows)
            print(f"  {year}: {len(rows)} matches")
        except Exception as e:
            print(f"  {year}: skipped ({e})")

    df = pd.DataFrame(all_rows)
    df = df.dropna(subset=["home_goals", "away_goals"])
    df["home_goals"] = df["home_goals"].astype(int)
    df["away_goals"] = df["away_goals"].astype(int)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def download_current_fixtures() -> pd.DataFrame:
    data = _fetch_json(CURRENT_YEAR)
    rows = _parse_matches(data, CURRENT_YEAR)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def refresh_all() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("Fetching historical World Cup results...")
    hist = download_historical()
    hist.to_csv(DATA_DIR / "international_results.csv", index=False)
    print(f"  Saved {len(hist)} completed matches -> data/raw/international_results.csv")

    print("Fetching 2026 World Cup fixtures...")
    fixtures = download_current_fixtures()
    fixtures.to_csv(DATA_DIR / "wc2026_fixtures.csv", index=False)
    print(f"  Saved {len(fixtures)} fixtures ({fixtures['home_goals'].notna().sum()} completed) -> data/raw/wc2026_fixtures.csv")


if __name__ == "__main__":
    refresh_all()
