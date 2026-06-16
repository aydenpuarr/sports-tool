"""World Cup 2026 betting-analysis dashboard.

Manual-decision-support only: this app never places bets. You read its
probability/edge breakdown, manually enter bookmaker odds you see in your
betting app, and place bets yourself if you choose to.
"""
from __future__ import annotations

from pathlib import Path
from datetime import date

import pandas as pd
import streamlit as st

from src.ingest.historical_results import load_results_csv
from src.ingest.openfootball import download_current_fixtures, refresh_all
from src.models.dixon_coles import ScorelineModel
from src.models.elo import EloRatings
from src.models.blend import build_match_view
from src.odds.manual_entry import OddsBook
from src.odds.value import evaluate_bet, BetTier
from src.query.parser import parse_query, Intent

st.set_page_config(page_title="WC 2026 Bet Analyzer", layout="wide", page_icon="⚽")

FIXTURES_PATH = Path("data/raw/wc2026_fixtures.csv")
RESULTS_PATH = Path("data/raw/international_results.csv")

TIER_COLOR = {
    BetTier.SAFE: ":green[SAFE ✓]",
    BetTier.VALUE: ":orange[VALUE/RISKY ⚡]",
    BetTier.NO_BET: ":gray[NO EDGE]",
}


@st.cache_resource
def load_models():
    if not RESULTS_PATH.exists():
        refresh_all()
    results = load_results_csv()
    elo = EloRatings()
    for _, row in results.iterrows():
        elo.update_match(
            row["home_team"], row["away_team"],
            int(row["home_goals"]), int(row["away_goals"]),
            competition=row.get("competition", "world_cup_final"),
            neutral_venue=bool(row.get("neutral_venue", True)),
        )
    scoreline_model = ScorelineModel()
    scoreline_model.fit(results)
    teams = sorted(set(results["home_team"]) | set(results["away_team"]))
    return elo, scoreline_model, teams


@st.cache_data(ttl=3600)
def load_fixtures() -> pd.DataFrame:
    if FIXTURES_PATH.exists():
        df = pd.read_csv(FIXTURES_PATH, parse_dates=["date"])
    else:
        df = download_current_fixtures()
    return df.sort_values("date").reset_index(drop=True)


def render_match_panel(
    elo: EloRatings,
    scoreline_model: ScorelineModel,
    home_team: str,
    away_team: str,
    odds_book: OddsBook,
    match_id: str,
    compact: bool = False,
) -> None:
    try:
        view = build_match_view(home_team, away_team, scoreline_model, elo, neutral_venue=True)
    except Exception as e:
        st.warning(f"Could not price {home_team} vs {away_team}: {e}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric(f"{home_team} win", f"{view.blended_home_win:.0%}")
    col2.metric("Draw", f"{view.blended_draw:.0%}")
    col3.metric(f"{away_team} win", f"{view.blended_away_win:.0%}")

    st.caption(
        f"Dixon-Coles: {view.dixon_coles.home_win:.0%} / {view.dixon_coles.draw:.0%} / {view.dixon_coles.away_win:.0%}  ·  "
        f"Elo: {view.elo_home_win:.0%} / {view.elo_draw:.0%} / {view.elo_away_win:.0%}  ·  "
        f"BTTS yes: {view.dixon_coles.btts_yes:.0%}  ·  Over 2.5: {view.dixon_coles.over_2_5:.0%}"
    )

    if not compact:
        st.write("**Top scorelines:**  " + "  ·  ".join(
            f"{h}-{a} ({p:.0%})" for (h, a), p in view.dixon_coles.top_scorelines
        ))

    st.write("**Enter bet365 odds → edge & stake suggestion:**")
    markets = {
        "home_win": (f"{home_team} win", view.blended_home_win),
        "draw": ("Draw", view.blended_draw),
        "away_win": (f"{away_team} win", view.blended_away_win),
        "btts_yes": ("BTTS Yes", view.dixon_coles.btts_yes),
        "over_2_5": ("Over 2.5", view.dixon_coles.over_2_5),
    }
    cols = st.columns(len(markets))
    for col, (key, (label, prob)) in zip(cols, markets.items()):
        odds = col.number_input(label, min_value=1.01, value=2.0, step=0.05, key=f"{match_id}_{key}")
        odds_book.set_odds(match_id, key, "bet365", odds)
        ev = evaluate_bet(label, prob, odds)
        col.write(f"{TIER_COLOR[ev.tier]}  edge {ev.edge:+.1%}  stake {ev.suggested_stake_fraction:.1%}")


def render_best_bets_scan(
    elo: EloRatings,
    scoreline_model: ScorelineModel,
    fixtures: pd.DataFrame,
    tier_filter: set[BetTier] | None = None,
    max_odds: float | None = None,
) -> None:
    """Score all upcoming (unplayed) fixtures and surface the top picks."""
    upcoming = fixtures[fixtures["home_goals"].isna()].copy()
    if upcoming.empty:
        st.info("No upcoming fixtures found in the cached data.")
        return

    rows = []
    for _, fix in upcoming.iterrows():
        home, away = fix["home_team"], fix["away_team"]
        try:
            view = build_match_view(home, away, scoreline_model, elo, neutral_venue=True)
        except Exception:
            continue

        for key, label, prob in [
            ("home_win", f"{home} win", view.blended_home_win),
            ("draw", "Draw", view.blended_draw),
            ("away_win", f"{away} win", view.blended_away_win),
            ("btts_yes", "BTTS Yes", view.dixon_coles.btts_yes),
            ("over_2_5", "Over 2.5", view.dixon_coles.over_2_5),
        ]:
            rows.append({
                "match": f"{home} vs {away}",
                "date": fix["date"],
                "market": label,
                "probability": prob,
                "tier": "SAFE" if prob >= 0.60 else ("VALUE" if prob >= 0.40 else "RISKY"),
            })

    df = pd.DataFrame(rows).sort_values("probability", ascending=False)

    if tier_filter:
        tier_names = {BetTier.SAFE: "SAFE", BetTier.VALUE: "VALUE"}
        names = {tier_names.get(t, "RISKY") for t in tier_filter}
        df = df[df["tier"].isin(names)]

    st.dataframe(
        df.head(30).style.format({"probability": "{:.0%}"}),
        width="stretch",
        hide_index=True,
    )


def main():
    st.title("⚽ World Cup 2026 Bet Analyzer")
    st.caption(
        "Elo + Dixon-Coles probabilities trained on 5 World Cups (2006-2022). "
        "Enter odds from bet365 manually — this tool never scrapes or auto-bets."
    )

    try:
        elo, scoreline_model, teams = load_models()
    except Exception as e:
        st.error(f"Failed to load models: {e}")
        return

    fixtures = load_fixtures()

    if "odds_book" not in st.session_state:
        st.session_state.odds_book = OddsBook()
    odds_book: OddsBook = st.session_state.odds_book

    tab_today, tab_browse, tab_chat = st.tabs(["Today / Upcoming", "Browse any match", "Ask the tool"])

    with tab_today:
        today = pd.Timestamp(date.today())
        upcoming = fixtures[fixtures["home_goals"].isna()].copy()
        this_week = upcoming[upcoming["date"] <= today + pd.Timedelta(days=7)]
        next_batch = this_week if not this_week.empty else upcoming.head(8)

        if next_batch.empty:
            st.info("No upcoming fixtures in the data. Run `python3 -m src.ingest.openfootball` to refresh.")
        else:
            st.subheader(f"Next {len(next_batch)} match(es)")
            for _, fix in next_batch.iterrows():
                home, away = fix["home_team"], fix["away_team"]
                fix_date = fix["date"].strftime("%a %d %b") if pd.notna(fix["date"]) else "TBC"
                with st.expander(f"**{home} vs {away}** — {fix_date}", expanded=len(next_batch) <= 3):
                    render_match_panel(
                        elo, scoreline_model, home, away, odds_book,
                        match_id=f"today_{home}_{away}", compact=True,
                    )

    with tab_browse:
        col_a, col_b = st.columns(2)
        home_team = col_a.selectbox("Home team", teams, index=0)
        away_team = col_b.selectbox("Away team", teams, index=min(1, len(teams) - 1))
        if home_team == away_team:
            st.warning("Pick two different teams.")
        else:
            render_match_panel(elo, scoreline_model, home_team, away_team, odds_book,
                               match_id=f"browse_{home_team}_{away_team}")

    with tab_chat:
        query_text = st.text_input("Ask: 'best bets today', 'Brazil vs Argentina stats', 'safe bets', 'value bets'…", "")
        if query_text:
            parsed = parse_query(query_text, teams)

            if parsed.intent == Intent.MATCH_STATS and len(parsed.teams) >= 2:
                st.subheader(f"{parsed.teams[0]} vs {parsed.teams[1]}")
                render_match_panel(
                    elo, scoreline_model, parsed.teams[0], parsed.teams[1], odds_book,
                    match_id=f"chat_{parsed.teams[0]}_{parsed.teams[1]}",
                )
            elif parsed.intent == Intent.SAFE_BETS:
                st.subheader("Safe bets across upcoming fixtures (model probability ≥ 60%)")
                render_best_bets_scan(elo, scoreline_model, fixtures,
                                      tier_filter={BetTier.SAFE}, max_odds=parsed.max_odds)
            elif parsed.intent == Intent.VALUE_BETS:
                st.subheader("Value / risky picks across upcoming fixtures")
                render_best_bets_scan(elo, scoreline_model, fixtures,
                                      tier_filter={BetTier.VALUE}, max_odds=parsed.max_odds)
            elif parsed.intent == Intent.BEST_BETS:
                st.subheader("Best bets across all upcoming fixtures")
                render_best_bets_scan(elo, scoreline_model, fixtures)
            else:
                st.warning(
                    "Couldn't understand that. Try: 'best bets today', 'safe bets under 1.5 odds', "
                    "'Brazil vs Argentina stats', or 'value bets'."
                )


if __name__ == "__main__":
    main()
