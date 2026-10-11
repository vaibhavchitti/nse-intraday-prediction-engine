from __future__ import annotations

from datetime import datetime, timedelta
from random import Random

from data.validation import normalize_timestamp, validate_candle


class SyntheticDataProvider:
    """Deterministic synthetic OHLCV provider used to exercise the pipeline without market data."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def fetch_candles(self, symbol: str, interval: str = "1min", start: str | None = None, end: str | None = None) -> list[dict]:
        symbol = symbol.upper()
        start_dt = normalize_timestamp(start or "2024-01-01T09:15:00+05:30")
        end_dt = normalize_timestamp(end or (start_dt + timedelta(minutes=10)))

        rng = Random(f"{self.seed}:{symbol}:{interval}")
        candles: list[dict] = []
        current = start_dt
        base = 100.0 + rng.random() * 10.0

        while current <= end_dt:
            open_price = round(base, 2)
            drift = (rng.random() - 0.5) * 2.5
            close_price = round(open_price + drift, 2)
            high_price = round(max(open_price, close_price) + abs(rng.random() * 1.5), 2)
            low_price = round(min(open_price, close_price) - abs(rng.random() * 1.5), 2)
            volume = max(100, int(1200 + rng.random() * 800))

            candle = validate_candle({
                "symbol": symbol,
                "timestamp": current,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "interval": interval,
            })
            candles.append(candle)
            current += timedelta(minutes=1)
            base = close_price

        return candles

    def fetch_latest_candle(self, symbol: str, interval: str = "1min") -> dict | None:
        candles = self.fetch_candles(symbol, interval=interval)
        return candles[-1] if candles else None


__all__ = ["SyntheticDataProvider"]
