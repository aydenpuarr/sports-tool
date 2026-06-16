"""In-memory/session storage schema for user-entered bookmaker odds.

bet365 (and most sportsbooks) prohibit automated scraping of their odds in
their Terms of Service, so odds always come from the user manually reading
and typing them in here -- this module just gives that a consistent shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OddsEntry:
    match_id: str
    market: str  # e.g. "home_win", "draw", "away_win", "btts_yes", "over_2_5"
    bookmaker: str  # e.g. "bet365"
    decimal_odds: float


@dataclass
class OddsBook:
    entries: dict[tuple[str, str, str], OddsEntry] = field(default_factory=dict)

    def set_odds(self, match_id: str, market: str, bookmaker: str, decimal_odds: float) -> None:
        key = (match_id, market, bookmaker)
        self.entries[key] = OddsEntry(match_id, market, bookmaker, decimal_odds)

    def get_odds(self, match_id: str, market: str, bookmaker: str = "bet365") -> float | None:
        entry = self.entries.get((match_id, market, bookmaker))
        return entry.decimal_odds if entry else None

    def markets_for_match(self, match_id: str) -> list[OddsEntry]:
        return [e for e in self.entries.values() if e.match_id == match_id]
