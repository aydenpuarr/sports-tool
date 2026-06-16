"""Structured intent parser for the dashboard chat box -- no LLM, $0 budget
(per the approved plan). Recognizes a fixed set of phrasing patterns and
extracts entities (team names, odds thresholds, tiers) to route to the same
query functions that power the dashboard tiles.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Intent(Enum):
    BEST_BETS = "best_bets"
    SAFE_BETS = "safe_bets"
    VALUE_BETS = "value_bets"
    MATCH_STATS = "match_stats"
    UNKNOWN = "unknown"


@dataclass
class ParsedQuery:
    intent: Intent
    teams: list[str] = field(default_factory=list)
    max_odds: float | None = None
    min_odds: float | None = None
    raw_text: str = ""


_ODDS_PATTERN = re.compile(r"(under|below|less than)\s+([\d.]+)|(over|above|greater than)\s+([\d.]+)")


def parse_query(text: str, known_teams: list[str]) -> ParsedQuery:
    lowered = text.lower().strip()

    teams = [t for t in known_teams if t.lower() in lowered]

    max_odds = min_odds = None
    for match in _ODDS_PATTERN.finditer(lowered):
        if match.group(2):
            max_odds = float(match.group(2))
        elif match.group(4):
            min_odds = float(match.group(4))

    if teams and ("stat" in lowered or "vs" in lowered or "probability" in lowered or "score" in lowered):
        intent = Intent.MATCH_STATS
    elif "safe" in lowered:
        intent = Intent.SAFE_BETS
    elif "risky" in lowered or "value" in lowered or "high odds" in lowered or "long shot" in lowered:
        intent = Intent.VALUE_BETS
    elif "best bet" in lowered or "best pick" in lowered or "what should i bet" in lowered:
        intent = Intent.BEST_BETS
    elif teams:
        intent = Intent.MATCH_STATS
    else:
        intent = Intent.UNKNOWN

    return ParsedQuery(intent=intent, teams=teams, max_odds=max_odds, min_odds=min_odds, raw_text=text)
