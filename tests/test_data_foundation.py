from datetime import datetime, timedelta

import pandas as pd
import pytest

from data.providers.csv_provider import CSVDataProvider
from data.providers.synthetic_provider import SyntheticDataProvider
from data.validation import CandleValidationError, normalize_timestamp, validate_candle, validate_candles


def test_normalize_timestamp_uses_ist():
    ts = normalize_timestamp("2024-01-01T09:15:00Z")
    assert ts.tzinfo is not None
    assert ts.utcoffset() == timedelta(hours=5, minutes=30)


def test_validate_candle_accepts_clean_data():
    candle = {
        "symbol": "RELIANCE",
        "timestamp": "2024-01-01T09:15:00+05:30",
        "open": 100.0,
        "high": 101.0,
        "low": 99.5,
        "close": 100.8,
        "volume": 1200,
        "interval": "1min",
    }

    result = validate_candle(candle)
    assert result["symbol"] == "RELIANCE"
    assert result["close"] == 100.8


def test_validate_candle_rejects_invalid_ranges_and_duplicates():
    bad = {
        "symbol": "RELIANCE",
        "timestamp": "2024-01-01T09:15:00+05:30",
        "open": 100.0,
        "high": 99.5,
        "low": 101.0,
        "close": 100.8,
        "volume": 1200,
        "interval": "1min",
    }

    with pytest.raises(CandleValidationError):
        validate_candle(bad)

    with pytest.raises(CandleValidationError):
        validate_candles([
            {
                "symbol": "RELIANCE",
                "timestamp": "2024-01-01T09:15:00+05:30",
                "open": 100.0,
                "high": 101.0,
                "low": 99.5,
                "close": 100.8,
                "volume": 1200,
                "interval": "1min",
            },
            {
                "symbol": "RELIANCE",
                "timestamp": "2024-01-01T09:15:00+05:30",
                "open": 101.0,
                "high": 102.0,
                "low": 100.5,
                "close": 101.8,
                "volume": 1300,
                "interval": "1min",
            },
        ])


def test_csv_provider_loads_and_validates_candles(tmp_path):
    csv_path = tmp_path / "reliance.csv"
    pd.DataFrame(
        [
            {
                "symbol": "RELIANCE",
                "timestamp": "2024-01-01 09:15:00",
                "open": 100.0,
                "high": 101.0,
                "low": 99.5,
                "close": 100.8,
                "volume": 1200,
                "interval": "1min",
            },
            {
                "symbol": "RELIANCE",
                "timestamp": "2024-01-01 09:16:00",
                "open": 100.8,
                "high": 101.2,
                "low": 100.4,
                "close": 101.1,
                "volume": 1300,
                "interval": "1min",
            },
        ]
    ).to_csv(csv_path, index=False)

    provider = CSVDataProvider(str(tmp_path))
    candles = provider.fetch_candles("RELIANCE", interval="1min")

    assert len(candles) == 2
    assert candles[0]["symbol"] == "RELIANCE"
    assert candles[1]["timestamp"]


def test_synthetic_provider_is_deterministic():
    provider = SyntheticDataProvider(seed=42)
    first = provider.fetch_candles("RELIANCE", interval="1min", start="2024-01-01T09:15:00+05:30", end="2024-01-01T09:18:00+05:30")
    second = provider.fetch_candles("RELIANCE", interval="1min", start="2024-01-01T09:15:00+05:30", end="2024-01-01T09:18:00+05:30")

    assert first == second
    assert len(first) == 4
    assert first[0]["symbol"] == "RELIANCE"
