from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from data.providers.csv_provider import CSVDataProvider
from data.providers.synthetic_provider import SyntheticDataProvider
from data.validation import to_ist, validate_candle_stream


@pytest.fixture
def sample_candles():
    now = datetime.now(timezone.utc)
    return [
        {
            "symbol": "RELIANCE",
            "timestamp": (now - timedelta(minutes=3)).isoformat(),
            "open": 100.0,
            "high": 101.5,
            "low": 99.5,
            "close": 101.0,
            "volume": 1500.0,
        },
        {
            "symbol": "RELIANCE",
            "timestamp": (now - timedelta(minutes=2)).isoformat(),
            "open": 101.0,
            "high": 102.0,
            "low": 100.5,
            "close": 101.8,
            "volume": 1700.0,
        },
    ]


def test_validate_candle_stream_accepts_valid_batch(sample_candles):
    result = validate_candle_stream(sample_candles, max_stale_minutes=30)
    assert len(result) == 2
    assert result[0]["symbol"] == "RELIANCE"


def test_validate_candle_stream_rejects_duplicates():
    candles = [
        {"symbol": "TCS", "timestamp": "2024-01-02T09:15:00+00:00", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000.0},
        {"symbol": "TCS", "timestamp": "2024-01-02T09:15:00+00:00", "open": 100.5, "high": 101.2, "low": 99.8, "close": 101.0, "volume": 1050.0},
    ]
    with pytest.raises(ValueError):
        validate_candle_stream(candles, max_stale_minutes=30)


def test_validate_candle_stream_rejects_invalid_ohlc():
    candles = [
        {"symbol": "ICICIBANK", "timestamp": "2024-01-02T09:15:00+00:00", "open": 100.0, "high": 95.0, "low": 94.0, "close": 99.0, "volume": 800.0},
    ]
    with pytest.raises(ValueError):
        validate_candle_stream(candles, max_stale_minutes=30)


def test_to_ist_converts_utc_to_indian_time():
    utc_time = datetime(2024, 1, 2, 9, 15, tzinfo=timezone.utc)
    ist_time = to_ist(utc_time)
    assert ist_time.tzinfo is not None
    assert ist_time.utcoffset().total_seconds() == 5 * 3600 + 30 * 60


def test_synthetic_provider_returns_ordered_candles():
    provider = SyntheticDataProvider(seed=42)
    candles = provider.fetch_candles("RELIANCE", start="2024-01-02T09:15:00", end="2024-01-02T09:17:00")
    assert len(candles) == 3
    assert candles[0]["symbol"] == "RELIANCE"
    assert candles[0]["timestamp"] <= candles[-1]["timestamp"]


def test_csv_provider_loads_csv_rows(tmp_path):
    csv_file = tmp_path / "RELIANCE.csv"
    csv_file.write_text(
        "symbol,timestamp,open,high,low,close,volume\n"
        "RELIANCE,2024-01-02T09:15:00+00:00,100,101,99,100.5,1000\n"
        "RELIANCE,2024-01-02T09:16:00+00:00,100.5,101.5,99.8,101.2,1100\n",
        encoding="utf-8",
    )
    provider = CSVDataProvider(tmp_path)
    rows = provider.fetch_candles("RELIANCE")
    assert len(rows) == 2
    assert rows[0]["symbol"] == "RELIANCE"
    assert rows[0]["timestamp"] <= rows[-1]["timestamp"]


def test_csv_provider_supports_time_filter(tmp_path):
    csv_file = tmp_path / "TCS.csv"
    csv_file.write_text(
        "symbol,timestamp,open,high,low,close,volume\n"
        "TCS,2024-01-02T09:15:00+00:00,101,102,100,101.5,2000\n"
        "TCS,2024-01-02T09:16:00+00:00,101.5,102.3,100.9,102.1,2200\n"
        "TCS,2024-01-02T09:17:00+00:00,102.1,103.0,101.4,102.8,2400\n",
        encoding="utf-8",
    )
    provider = CSVDataProvider(tmp_path)
    rows = provider.fetch_candles("TCS", start="2024-01-02T09:16:00+00:00", end="2024-01-02T09:17:00+00:00")
    assert len(rows) == 2
    assert rows[0]["timestamp"].isoformat() == "2024-01-02T09:16:00+00:00"


__all__ = ["sample_candles"]
