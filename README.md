# World Cup 2026 Bet Analyzer

A personal, $0-budget, data-driven decision-support tool for World Cup 2026 betting. It estimates match probabilities from historical results (Elo + Dixon-Coles), lets you compare those against odds you manually enter from your sportsbook (e.g. bet365), and flags "safe" vs "value/risky" bets. **It never scrapes odds or places bets automatically** -- most sportsbooks, including bet365, prohibit bots/automated scraping in their Terms of Service.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Drop a historical international-results CSV at `data/raw/international_results.csv` with columns:
`date, home_team, away_team, home_goals, away_goals[, competition, neutral_venue]`

Good free sources: [OpenFootball](https://github.com/openfootball/worldcup.json), Kaggle World Cup historical datasets, or [football-data.org](https://www.football-data.org)'s free tier export. Without this file the app will show an error telling you where to put it.

## Run

```bash
.venv/bin/streamlit run app.py
```

## Run tests

```bash
.venv/bin/pip install pytest
.venv/bin/python3 -m pytest tests/ -v
```

## Layout

- `src/models/elo.py` -- eloratings.net-style national team Elo ratings.
- `src/models/dixon_coles.py` -- wraps `penaltyblog`'s Dixon-Coles goal model for 1X2/BTTS/O-U/correct-score probabilities.
- `src/models/features.py` / `blend.py` -- squad continuity (chemistry), club form, and weather adjustments blended with Elo + Dixon-Coles.
- `src/odds/` -- manual odds entry + implied probability / edge / fractional-Kelly stake sizing, safe vs. value vs. no-bet tiering.
- `src/ingest/` -- historical results loader, Open-Meteo weather client, football-data.org fixtures client.
- `src/backtest/walkforward.py` -- walk-forward backtest (no lookahead bias) with Brier score / RPS calibration metrics.
- `src/query/parser.py` -- structured (non-LLM) intent parser for the dashboard's chat box.
- `app.py` -- Streamlit dashboard.
