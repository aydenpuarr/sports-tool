"""football-data.org client for World Cup fixtures/results.

Free tier: 10 requests/minute, registered (free) API token required --
register at https://www.football-data.org/client/register to get a token,
no credit card. Personal/non-commercial use only per their ToS.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import requests

BASE_URL = "https://api.football-data.org/v4"
WORLD_CUP_COMPETITION_CODE = "WC"


@dataclass
class Fixture:
    match_id: str
    utc_date: str
    home_team: str
    away_team: str
    status: str
    home_goals: int | None
    away_goals: int | None


def _headers() -> dict:
    token = os.environ.get("FOOTBALL_DATA_API_TOKEN")
    if not token:
        raise RuntimeError(
            "Set FOOTBALL_DATA_API_TOKEN (free, no card, register at "
            "football-data.org/client/register) before fetching fixtures."
        )
    return {"X-Auth-Token": token}


def get_world_cup_fixtures(status: str | None = None) -> list[Fixture]:
    """status: 'SCHEDULED', 'LIVE', 'FINISHED', or None for all."""
    params = {"status": status} if status else {}
    resp = requests.get(
        f"{BASE_URL}/competitions/{WORLD_CUP_COMPETITION_CODE}/matches",
        headers=_headers(),
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    matches = resp.json().get("matches", [])

    fixtures = []
    for m in matches:
        score = m.get("score", {}).get("fullTime", {})
        fixtures.append(
            Fixture(
                match_id=str(m["id"]),
                utc_date=m["utcDate"],
                home_team=m["homeTeam"]["name"],
                away_team=m["awayTeam"]["name"],
                status=m["status"],
                home_goals=score.get("home"),
                away_goals=score.get("away"),
            )
        )
    return fixtures
