from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Optional

from data.validation import validate_candle_stream


class CSVDataProvider:
    """Simple historical CSV loader for offline research.

    Expects one file per symbol, named <symbol>.csv, with columns:
    symbol,timestamp,open,high,low,close,volume
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

    def _resolve_path(self, symbol: str) -> Path:
        base_name = str(symbol).strip()
        if not base_name:
            raise ValueError("Symbol cannot be empty")
        return self.data_dir / f"{base_name}.csv"

    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1min",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[dict]:
        path = self._resolve_path(symbol)
        if not path.exists():
            raise FileNotFoundError(f"No CSV data found for symbol {symbol!r} at {path}")

        rows: List[dict] = []
        with path.open("r", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row:
                    continue
                normalized = {
                    "symbol": row.get("symbol", symbol).strip(),
                    "timestamp": row["timestamp"].strip(),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
                rows.append(normalized)

        if start is not None or end is not None:
            rows = self._filter_by_time(rows, start=start, end=end)

        return validate_candle_stream(rows)

    def fetch_latest_candle(self, symbol: str, interval: str = "1min") -> Optional[dict]:
        candles = self.fetch_candles(symbol, interval=interval)
        return candles[-1] if candles else None

    @staticmethod
    def _filter_by_time(rows: List[dict], *, start: Optional[str], end: Optional[str]) -> List[dict]:
        if not rows:
            return rows
        filtered = rows
        if start is not None:
            start_dt = __import__("datetime").datetime.fromisoformat(start)
            filtered = [row for row in filtered if __import__("datetime").datetime.fromisoformat(row["timestamp"]) >= start_dt]
        if end is not None:
            end_dt = __import__("datetime").datetime.fromisoformat(end)
            filtered = [row for row in filtered if __import__("datetime").datetime.fromisoformat(row["timestamp"]) <= end_dt]
        return filtered


__all__ = ["CSVDataProvider"]
