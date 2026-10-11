from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from data.validation import validate_candle_stream


class SyntheticDataProvider:
    """Deterministic synthetic intraday data generator for tests and offline research."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1min",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[dict]:
        start_dt = self._parse_datetime(start or "2024-01-02T09:15:00")
        end_dt = self._parse_datetime(end or "2024-01-02T09:18:00")
        if end_dt <= start_dt:
            return []

        candles: List[dict] = []
        current = start_dt
        base_price = 100.0
        drift = 0.15
        phase = 0.0

        while current <= end_dt:
            phase += 1.0
            price = base_price + (phase * drift) + (self.seed % 5) * 0.1
            open_price = price
            close_price = price + 0.9 * (phase % 3 - 1)
            high_price = max(open_price, close_price) + 0.8
            low_price = min(open_price, close_price) - 0.7
            volume = 1000 + int((phase * 17) % 200)

            candles.append(
                {
                    "symbol": symbol,
                    "timestamp": current.isoformat(),
                    "open": round(open_price, 4),
                    "high": round(high_price, 4),
                    "low": round(low_price, 4),
                    "close": round(close_price, 4),
                    "volume": volume,
                }
            )
            current += timedelta(minutes=1)

        return validate_candle_stream(candles, max_stale_minutes=60)

    def fetch_latest_candle(self, symbol: str, interval: str = "1min") -> Optional[dict]:
        candles = self.fetch_candles(symbol, interval=interval)
        return candles[-1] if candles else None

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


__all__ = ["SyntheticDataProvider"]
