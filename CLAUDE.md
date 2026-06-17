# CLAUDE.md — World Cup 2026 Bet Analyzer

## What this project is

A personal, $0-budget, data-driven betting decision-support tool for the 2026 FIFA World Cup. It estimates match probabilities using historical World Cup data, surfaces "safe" and "value/risky" bets, and lets the user manually enter bookmaker odds to see where they have an edge.

**It never places bets automatically and never scrapes bookmaker sites** — bet365 and others prohibit bots in their ToS. Odds are always entered manually by the user.

---

## How to run it

```bash
# One-time setup
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Every time you want to use the tool
PYTHONPATH=. .venv/bin/streamlit run app.py
```

The browser opens automatically at `http://localhost:8501`. The first run auto-downloads real World Cup fixture data from OpenFootball (public domain, no API key needed).

## How to run tests

```bash
PYTHONPATH=. .venv/bin/python3 -m pytest tests/ -v
```

All 17 tests should pass. If any fail, the most likely cause is a missing dependency — run `pip install -r requirements.txt` again.

## Important: PYTHONPATH

Always prefix commands with `PYTHONPATH=.` or the imports will fail. The `src/` package needs the project root on the path. In a remote Claude Code session this is set automatically via the session-start hook (`.claude/hooks/session-start.sh`), but locally you need to set it yourself.

---

## Project structure

```
sports-tool/
  app.py                        # Streamlit dashboard — main entrypoint
  requirements.txt              # All dependencies
  data/
    raw/
      international_results.csv # 320 historical WC matches (2006-2022), auto-downloaded
      wc2026_fixtures.csv       # Live 2026 fixtures (104 matches), auto-downloaded
  src/
    ingest/
      openfootball.py           # Downloads real data from OpenFootball GitHub (run to refresh)
      historical_results.py     # Loads data/raw/international_results.csv into a DataFrame
      fixtures.py               # football-data.org client (needs free API token, optional)
      weather.py                # Open-Meteo client (free, no key, for weather factors)
    models/
      elo.py                    # National team Elo ratings (eloratings.net methodology)
      dixon_coles.py            # Wraps penaltyblog's Dixon-Coles goal model
      features.py               # Squad chemistry, club form, weather adjustments
      blend.py                  # Combines Elo + Dixon-Coles + feature adjustments
    odds/
      manual_entry.py           # In-memory schema for user-entered bookmaker odds
      value.py                  # Edge calculation, Kelly criterion, safe/value/no-bet tiering
    backtest/
      walkforward.py            # Walk-forward backtest harness (Brier score, RPS metrics)
    query/
      parser.py                 # Structured intent parser for the dashboard chat box
  tests/
    test_elo.py                 # 6 tests for Elo model
    test_dixon_coles.py         # 4 tests for Dixon-Coles wrapper
    test_value.py               # 7 tests for odds/Kelly/tier logic
  .claude/
    hooks/session-start.sh      # Auto-installs dependencies on Claude Code web sessions
    settings.json               # Registers the session-start hook
```

---

## How the model works

The tool uses two statistical models blended together:

### 1. Elo ratings (`src/models/elo.py`)
- Each national team has a rating (default 1500)
- Updated after every match using the eloratings.net methodology:
  - K factor varies by competition importance (60 for World Cup final, 20 for friendly)
  - Goal difference scales the rating change (a 4-0 win moves ratings more than 1-0)
  - Home advantage = +100 rating points (all WC matches are neutral venue so this is off)
- Gives a rough win/draw/loss probability split

### 2. Dixon-Coles Poisson model (`src/models/dixon_coles.py`)
- Fits attack and defence strength ratings for each team from historical scorelines
- Uses the `penaltyblog` Python package (`penaltyblog.models.DixonColesGoalModel`)
- Outputs a full scoreline probability grid (e.g. P(Brazil 2-1 Argentina) = 9%)
- From that grid it reads: 1X2, BTTS, Over/Under 2.5, correct score probabilities
- Time-decay weighting: recent matches count more than old ones (half-life = 365 days)

### 3. Blending (`src/models/blend.py`)
- Dixon-Coles is the primary source (70% weight), Elo is a cross-check (30% weight)
- Squad chemistry (teammates sharing the same club), club form (G+A per 90 last season), and weather (heat/humidity penalty for high-press teams) nudge the blended probabilities slightly

### 4. Bet tiering (`src/odds/value.py`)
- **SAFE**: model probability ≥ 60%, odds ≤ 1.80, positive edge vs entered odds
- **VALUE/RISKY**: positive edge ≥ 5% but below the safe threshold — worth considering
- **NO EDGE**: bookmaker implied probability exceeds the model's — skip
- Suggested stake uses fractional Kelly (full Kelly ÷ 4) to limit variance

---

## Data sources (all free, no credit card)

| Source | What it provides | Key fact |
|---|---|---|
| OpenFootball (GitHub) | WC results 1930–2026, fixtures | Public domain, no API key |
| Open-Meteo | Weather forecasts + historical archive | No key, global coverage |
| football-data.org | Live fixtures/lineups (optional) | Free tier, needs a free token |

To refresh the fixture/results data:
```bash
PYTHONPATH=. .venv/bin/python3 -m src.ingest.openfootball
```

---

## Common errors and fixes

**`ModuleNotFoundError: No module named 'src'`**
→ You're missing `PYTHONPATH=.`. Prefix every command with it:
```bash
PYTHONPATH=. .venv/bin/streamlit run app.py
```

**`FileNotFoundError: No historical results file at data/raw/international_results.csv`**
→ The data hasn't been downloaded yet. Run:
```bash
PYTHONPATH=. .venv/bin/python3 -m src.ingest.openfootball
```

**`ValueError: buffer source array is read-only`**
→ This was a bug in the Dixon-Coles model's numpy array handling. It is already fixed in `src/models/dixon_coles.py` — all arrays are copied with `copy=True` before being passed to penaltyblog.

**`penaltyblog not found` or any import error on first run**
→ Dependencies not installed. Run:
```bash
.venv/bin/pip install -r requirements.txt
```

**Streamlit `use_container_width` deprecation warning**
→ Already fixed in `app.py`, safe to ignore if it appears.

---

## Branch

Active development branch: `claude/adoring-volta-ld09h9`

This branch contains all the code. It has not yet been merged into `main`.
