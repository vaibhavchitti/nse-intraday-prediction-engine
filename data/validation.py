from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class CandleValidationError(ValueError):
    """Raised when a candle is malformed, stale, duplicated, or invalid."""


def normalize_timestamp(value) -> datetime:
    """Normalize a timestamp to Asia/Kolkata timezone with a timezone-aware datetime."""
    if value is None:
        raise CandleValidationError("Timestamp is required")

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise CandleValidationError("Timestamp is required")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    else:
        raise CandleValidationError(f"Unsupported timestamp value: {type(value)!r}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def to_ist(value) -> datetime:
    return normalize_timestamp(value)


def validate_candle(candle: dict) -> dict:
    """Validate a single candle and return a normalized dictionary."""
    if not isinstance(candle, dict):
        raise CandleValidationError("Candle payload must be a dictionary")

    symbol = str(candle.get("symbol", "")).strip().upper()
    if not symbol:
        raise CandleValidationError("symbol is required")

    timestamp = normalize_timestamp(candle.get("timestamp"))
    open_price = float(candle.get("open"))
    high_price = float(candle.get("high"))
    low_price = float(candle.get("low"))
    close_price = float(candle.get("close"))
    volume = candle.get("volume")

    if volume is None:
        raise CandleValidationError(f"volume is required for {symbol} at {timestamp.isoformat()}")
    volume = float(volume)
    if volume < 0:
        raise CandleValidationError(f"volume cannot be negative for {symbol} at {timestamp.isoformat()}")

    for name, value in {
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
    }.items():
        if not math.isfinite(value):
            raise CandleValidationError(f"{name} must be finite for {symbol}")

    if high_price < max(open_price, close_price):
        raise CandleValidationError(f"high must be >= max(open, close) for {symbol} at {timestamp.isoformat()}")
    if low_price > min(open_price, close_price):
        raise CandleValidationError(f"low must be <= min(open, close) for {symbol} at {timestamp.isoformat()}")

    normalized = dict(candle)
    normalized["symbol"] = symbol
    normalized["timestamp"] = timestamp
    normalized["open"] = open_price
    normalized["high"] = high_price
    normalized["low"] = low_price
    normalized["close"] = close_price
    normalized["volume"] = volume
    return normalized


def validate_candles(candles: Sequence[dict], *, max_stale_minutes: int = 30, allow_future: bool = False) -> list[dict]:
    """Validate an ordered or unordered candle batch, detect duplicates, and sort by timestamp."""
    if candles is None:
        return []

    validated: list[dict] = []
    seen: set[tuple[str, datetime]] = set()

    for candle in candles:
        normalized = validate_candle(candle)
        key = (normalized["symbol"], normalized["timestamp"])
        if key in seen:
            raise CandleValidationError(f"Duplicate candle for {normalized['symbol']} at {normalized['timestamp'].isoformat()}")
        seen.add(key)
        validated.append(normalized)

    validated.sort(key=lambda item: item["timestamp"])

    if not allow_future:
        newest = max((item["timestamp"] for item in validated), default=None)
        if newest is not None and newest > datetime.now(IST) + timedelta(minutes=2):
            raise CandleValidationError("Future timestamps detected in candle stream")

    if max_stale_minutes is not None and validated:
        oldest = min(item["timestamp"] for item in validated)
        stale_cutoff = datetime.now(IST) - timedelta(minutes=max_stale_minutes)
        if oldest < stale_cutoff:
            raise CandleValidationError("Candle stream contains stale timestamps beyond the configured freshness threshold")

    return validated


def validate_candle_stream(candles: Iterable[dict], *, max_stale_minutes: int = 30, allow_future: bool = False) -> list[dict]:
    return validate_candles(candles, max_stale_minutes=max_stale_minutes, allow_future=allow_future)


__all__ = [
    "CandleValidationError",
    "IST",
    "normalize_timestamp",
    "to_ist",
    "validate_candle",
    "validate_candles",
    "validate_candle_stream",
]
