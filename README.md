# NSE Intraday Prediction Engine

A research-only Python project for evaluating intraday NSE cash-market forecasting approaches in GitHub Codespaces.

This repository intentionally does not place orders or connect to order-placement endpoints. It focuses on:
- historical-data replay
- deterministic synthetic generation for tests
- validation of timeline and OHLCV integrity
- backtesting and forecasting modules
- ledger-backed outcome validation
- safe live-data integration with credential checks

## Milestones completed

This repository now contains working foundations for the full milestone sequence:
- Milestone 1: configuration, validation, and offline provider foundation
- Milestone 2: historical research features, baselines, and walk-forward evaluation
- Milestone 3: immutable ledger and validation of matured outcomes
- Milestone 4: ORB and mean-reversion strategies
- Milestone 5: safe live-data provider shell for FYERS without blocking offline use
- Milestone 6: dashboard state layer and lightweight UI entry point
- Milestone 7: scan runner with overlap guards and retry-safe execution
- Milestone 8: conservative expansion analysis for limited-universe growth

## Codespaces setup

```bash
cd /workspaces/nse-intraday-prediction-engine
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
```

## Manual scan runner

```bash
cd /workspaces/nse-intraday-prediction-engine
source .venv/bin/activate
python scripts/manual_scan.py
```

## Streamlit dashboard

```bash
cd /workspaces/nse-intraday-prediction-engine
source .venv/bin/activate
streamlit run dashboard/streamlit_app.py
```

To enable the free Yahoo Finance data path for recent market snapshots, install the dependency and set:

```bash
source .venv/bin/activate
python -m pip install yfinance
export USE_YAHOO_DATA=1
streamlit run dashboard/streamlit_app.py
```

For Yahoo Finance, intraday data is generally available only for recent windows, so the provider uses a recent 7-day range by default.

### 5-minute ORB research watchlist

The dashboard's **Refresh ORB candidates** action ranks the configured 20-symbol core universe using recent Yahoo Finance 5-minute and daily candles, available bid/ask quotes, NIFTY candles, and mapped sector-index candles. It uses the 9:15-9:30 opening range, waits for a completed 5-minute close outside that range, and scores only the first retest. The projected target is one opening-range width beyond the breakout; the stop is the retest candle's low/high.

The 100-point research rubric allocates 25 points to 20-session liquidity and spread, 20 to same-time relative volume, 20 to ORB and retest, 15 to VWAP and RSI, 10 to NIFTY and sector alignment, and 10 to reward/risk and freshness. Relative volume compares cumulative volume through the current 5-minute slot with the previous five sessions. Daily traded value is estimated as close times volume if the provider does not return turnover.

The NSE pre-open feed alone cannot confirm an intraday setup. Missing history, quotes, or reference data earns no points for that component, and stale candles prevent eligibility. The listed filters and score are initial, unvalidated research criteria, not a profitability claim or a trading recommendation.

## Environment variables

The default environment template is provided in [.env.example](.env.example). For local-only experimentation, copy it and adjust only the values you actually need:

```bash
cp .env.example .env
```

Live broker access remains optional and is not required for the historical-data and synthetic-data paths.

## Research-only disclaimer

This project is for research, simulation, and evaluation only. It does not provide live trading execution, signal-based order placement, or brokerage integration.
