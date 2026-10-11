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

## Environment variables

The default environment template is provided in [.env.example](.env.example). For local-only experimentation, copy it and adjust only the values you actually need:

```bash
cp .env.example .env
```

Live broker access remains optional and is not required for the historical-data and synthetic-data paths.

## Research-only disclaimer

This project is for research, simulation, and evaluation only. It does not provide live trading execution, signal-based order placement, or brokerage integration.
