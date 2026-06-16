"""Feature engineering: squad continuity (chemistry), club form, and weather.

These produce small multiplicative adjustments to a team's expected-goals
rate, applied on top of the Elo/Dixon-Coles base ratings rather than being
treated as primary signals (per Groll et al. 2018's "team structure"
approach: number of shared-club teammates and recent club-season minutes
are the most replicable hobbyist-grade features for national-team squads).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Player:
    name: str
    club: str
    club_goals_last_season: float = 0.0
    club_assists_last_season: float = 0.0
    club_minutes_last_season: int = 0
    caps: int = 0


def squad_continuity_score(squad: list[Player]) -> float:
    """Fraction of likely-starting-XI players who share a club with at least
    one teammate, as a proxy for on-pitch chemistry. 0-1, higher = more shared
    club experience."""
    if not squad:
        return 0.0
    club_counts: dict[str, int] = {}
    for p in squad:
        club_counts[p.club] = club_counts.get(p.club, 0) + 1
    shared = sum(count for count in club_counts.values() if count > 1)
    return shared / len(squad)


def club_form_index(squad: list[Player]) -> float:
    """Average (goals + assists) per 90 minutes across the squad last club
    season, as a proxy for "players in form". Returns a multiplier centered
    on 1.0 where ~1.0 is average production."""
    contributions = []
    for p in squad:
        if p.club_minutes_last_season <= 0:
            continue
        per90 = (p.club_goals_last_season + p.club_assists_last_season) / (
            p.club_minutes_last_season / 90.0
        )
        contributions.append(per90)
    if not contributions:
        return 1.0
    avg = sum(contributions) / len(contributions)
    baseline = 0.35  # rough league-average G+A/90 for an outfield squad mix
    return max(0.7, min(1.3, avg / baseline))


def weather_adjustment(temperature_c: float, humidity_pct: float, high_press_team: bool) -> float:
    """Small expected-goals multiplier for heat/humidity. High heat+humidity
    tends to slow down high-press, high-tempo teams more than others.
    Returns a multiplier close to 1.0 (0.9-1.0 range)."""
    if temperature_c < 28 and humidity_pct < 60:
        return 1.0
    heat_penalty = min(0.1, max(0.0, (temperature_c - 28) / 100.0))
    humidity_penalty = min(0.05, max(0.0, (humidity_pct - 60) / 400.0))
    penalty = heat_penalty + humidity_penalty
    if high_press_team:
        penalty *= 1.5
    return max(0.85, 1.0 - penalty)


def combined_attack_multiplier(
    squad: list[Player],
    temperature_c: float,
    humidity_pct: float,
    high_press_team: bool,
) -> float:
    """Combines chemistry, club form, and weather into one multiplier applied
    to a team's Dixon-Coles attack strength / expected goals."""
    chemistry = 0.95 + 0.1 * squad_continuity_score(squad)  # 0.95-1.05
    form = club_form_index(squad)
    weather = weather_adjustment(temperature_c, humidity_pct, high_press_team)
    return chemistry * form * weather
