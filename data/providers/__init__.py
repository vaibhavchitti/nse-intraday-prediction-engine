from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Sequence

from data.providers.base import DataValidationError


def to_ist(value: datetime | str) -> datetime:
    """Return a timezone-aware datetime normalized to Asia/Kolkata."""
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Unsupported datetime string: {value!r}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone(timedelta(hours=5, minutes=30)))

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone(timedelta(hours=5, minutes=30)))


def validate_candle_stream(
    candles: Sequence[dict],
    *,
    max_stale_minutes: int = 10,
    now: datetime | None = None,
) -> List[dict]:
    """Validate a stream of candles and normalize timestamps to IST."""
    if not candles:
        raise DataValidationError("No candles were supplied")

    normalized: List[dict] = []
    previous_ts: datetime | None = None
    current_time = now or datetime.now(timezone.utc)

    for idx, candle in enumerate(candles):
        if not isinstance(candle, dict):
            raise DataValidationError(f"Candle at index {idx} is not a dictionary")

        missing = [field for field in ("symbol", "timestamp", "open", "high", "low", "close", "volume") if field not in candle]
        if missing:
            raise DataValidationError(f"Candle at index {idx} is missing required fields: {missing}")

        symbol = str(candle["symbol"]).strip()
        if not symbol:
            raise DataValidationError(f"Candle at index {idx} has empty symbol")

        ts = to_ist(candle["timestamp"])
        if previous_ts is not None and ts <= previous_ts:
            raise DataValidationError(f"Candle timestamps are not strictly increasing for {symbol}")

        open_price = float(candle["open"])
        high_price = float(candle["high"])
        low_price = float(candle["low"])
        close_price = float(candle["close"])
        volume = candle["volume"]

        if not all(value > 0 for value in (open_price, high_price, low_price, close_price)):
            raise DataValidationError(f"Candle for {symbol} at {ts.isoformat()} must have positive OHLC values")
        if high_price < max(open_price, close_price):
            raise DataValidationError(f"High price is below the candle body for {symbol} at {ts.isoformat()}")
        if low_price > min(open_price, close_price):
            raise DataValidationError(f"Low price exceeds the candle body for {symbol} at {ts.isoformat()}")
        if volume is None or float(volume) < 0:
            raise DataValidationError(f"Volume for {symbol} at {ts.isoformat()} is invalid")

        age_minutes = (current_time.astimezone(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds() / 60.0
        if age_minutes > max_stale_minutes:
            raise DataValidationError(f"Candle for {symbol} at {ts.isoformat()} is stale (> {max_stale_minutes} minutes)")

        normalized.append(
            {
                "symbol": symbol,
                "timestamp": ts,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": float(volume),
            }
        )
        previous_ts = ts

    return normalized


__all__ = ["to_ist", "validate_candle_stream"]
