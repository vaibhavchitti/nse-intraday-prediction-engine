# NSE Intraday Prediction Engine

A research-only Python project for evaluating intraday NSE cash-market forecasting approaches in Codespaces.

This repository intentionally does not place orders or connect to broker order endpoints. It focuses on:
- historical-data replay
- deterministic synthetic generation for tests
- validation of timeline and OHLCV integrity
- future backtesting and forecasting modules

## Repository structure

- `config.py` — environment-based settings
- `data/validation.py` — candle validation and timestamp normalization
- `data/providers/base.py` — provider interface and exceptions
- `data/providers/csv_provider.py` — offline CSV ingestion
- `data/providers/synthetic_provider.py` — deterministic synthetic data for tests
- `tests/` — pytest coverage for the data foundation
- `scripts/ensure_dirs.py` — local utility to create the initial project directories

## Codespaces setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Environment variables

Copy the sample file and adjust only the values you actually need:

```bash
cp .env.example .env
```

The app is intentionally credential-light. Live broker access is optional and is not required for this Milestone 1 research foundation.

## Research-only disclaimer

This project is for research, simulation, and evaluation only. It does not provide live trading execution, signal-based order placement, or brokerage integration.
