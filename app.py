"""World Cup 2026 betting-analysis dashboard.

Manual-decision-support only: this app never places bets. You read its
probability/edge breakdown, manually enter bookmaker odds you see in your
betting app, and place bets yourself if you choose to.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd

from src.ingest.historical_results import load_results_csv
from src.models.dixon_coles import ScorelineModel
from src.models.elo import EloRatings
from src.models.blend import build_match_view
from src.odds.manual_entry import OddsBook
from src.odds.value import evaluate_bet, BetTier
from src.query.parser import parse_query, Intent

st.set_page_config(page_title="World Cup 2026 Bet Analyzer", layout="wide")


@st.cache_resource
def load_models():
    results = load_results_csv()
    elo = EloRatings()
    for _, row in results.iterrows():
        elo.update_match(
            row["home_team"], row["away_team"], row["home_goals"], row["away_goals"],
            competition=row.get("competition", "qualifier"),
            neutral_venue=bool(row.get("neutral_venue", False)),
        )
    scoreline_model = ScorelineModel()
    scoreline_model.fit(results)
    teams = sorted(set(results["home_team"]) | set(results["away_team"]))
    return elo, scoreline_model, teams


def render_match_panel(elo, scoreline_model, home_team: str, away_team: str, odds_book: OddsBook, match_id: str):
    view = build_match_view(home_team, away_team, scoreline_model, elo, neutral_venue=True)

    col1, col2, col3 = st.columns(3)
    col1.metric(f"{home_team} win", f"{view.blended_home_win:.0%}")
    col2.metric("Draw", f"{view.blended_draw:.0%}")
    col3.metric(f"{away_team} win", f"{view.blended_away_win:.0%}")

    st.caption(
        f"Dixon-Coles: {view.dixon_coles.home_win:.0%}/{view.dixon_coles.draw:.0%}/{view.dixon_coles.away_win:.0%}  ·  "
        f"Elo: {view.elo_home_win:.0%}/{view.elo_draw:.0%}/{view.elo_away_win:.0%}  ·  "
        f"BTTS yes: {view.dixon_coles.btts_yes:.0%}  ·  Over 2.5: {view.dixon_coles.over_2_5:.0%}"
    )

    st.write("**Top scorelines:**", ", ".join(f"{h}-{a} ({p:.0%})" for (h, a), p in view.dixon_coles.top_scorelines))

    st.write("**Enter bet365 odds to evaluate value:**")
    markets = {
        "home_win": (f"{home_team} win", view.blended_home_win),
        "draw": ("Draw", view.blended_draw),
        "away_win": (f"{away_team} win", view.blended_away_win),
        "btts_yes": ("BTTS Yes", view.dixon_coles.btts_yes),
        "over_2_5": ("Over 2.5 goals", view.dixon_coles.over_2_5),
    }
    cols = st.columns(len(markets))
    for col, (key, (label, prob)) in zip(cols, markets.items()):
        odds = col.number_input(label, min_value=1.01, value=2.0, step=0.05, key=f"{match_id}_{key}")
        odds_book.set_odds(match_id, key, "bet365", odds)
        evaluation = evaluate_bet(label, prob, odds)
        tier_label = {
            BetTier.SAFE: ":green[SAFE]",
            BetTier.VALUE: ":orange[VALUE/RISKY]",
            BetTier.NO_BET: ":gray[NO EDGE]",
        }[evaluation.tier]
        col.write(f"{tier_label}  edge {evaluation.edge:+.1%}  stake {evaluation.suggested_stake_fraction:.1%} of bankroll")


def main():
    st.title("World Cup 2026 Bet Analyzer")
    st.caption(
        "Data-driven match probabilities (Elo + Dixon-Coles), backtested on historical results. "
        "You enter odds manually and place any bets yourself -- this tool never scrapes or auto-bets on bet365."
    )

    try:
        elo, scoreline_model, teams = load_models()
    except FileNotFoundError as e:
        st.error(str(e))
        st.info("Drop a historical results CSV into data/raw/international_results.csv to get started.")
        return

    if "odds_book" not in st.session_state:
        st.session_state.odds_book = OddsBook()
    odds_book: OddsBook = st.session_state.odds_book

    tab_browse, tab_chat = st.tabs(["Browse matches", "Ask the tool"])

    with tab_browse:
        col_a, col_b = st.columns(2)
        home_team = col_a.selectbox("Home team", teams, index=0)
        away_team = col_b.selectbox("Away team", teams, index=min(1, len(teams) - 1))
        if home_team == away_team:
            st.warning("Pick two different teams.")
        else:
            render_match_panel(elo, scoreline_model, home_team, away_team, odds_book, match_id=f"{home_team}_{away_team}")

    with tab_chat:
        query_text = st.text_input("Ask about matches, stats, or bet recommendations", "")
        if query_text:
            parsed = parse_query(query_text, teams)
            if parsed.intent == Intent.MATCH_STATS and len(parsed.teams) >= 2:
                render_match_panel(
                    elo, scoreline_model, parsed.teams[0], parsed.teams[1], odds_book,
                    match_id=f"chat_{parsed.teams[0]}_{parsed.teams[1]}",
                )
            elif parsed.intent in (Intent.SAFE_BETS, Intent.VALUE_BETS, Intent.BEST_BETS):
                st.info(
                    "This view needs the current tournament's live fixture list "
                    "(see src/ingest/fixtures.py) wired in to scan all upcoming matches at once. "
                    "For now, use the Browse tab to evaluate a specific matchup, or mention two team "
                    "names here, e.g. 'Brazil vs Argentina safe bets under 1.5 odds'."
                )
            else:
                st.warning("Couldn't understand that. Try mentioning two team names, or ask for 'safe bets' / 'value bets'.")


if __name__ == "__main__":
    main()
