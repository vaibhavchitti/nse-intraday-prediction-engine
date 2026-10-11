from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from data.validation import CandleValidationError, validate_candle


class CSVDataProvider:
    """Simple offline provider that reads OHLCV data from CSV files."""

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)

    def _candidate_files(self, symbol: str):
        if self.base_path.is_file():
            return [self.base_path]

        pattern = f"{symbol.upper()}.csv"
        return sorted(self.base_path.glob("*.csv")) if self.base_path.exists() else []

    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1min",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> list[dict]:
        symbol = symbol.upper()
        rows: list[dict] = []
        start_dt = None
        end_dt = None

        if start is not None:
            start_dt = pd.Timestamp(start).tz_localize(None) if pd.Timestamp(start).tzinfo is None else pd.Timestamp(start).tz_convert("UTC").tz_localize(None)
        if end is not None:
            end_dt = pd.Timestamp(end).tz_localize(None) if pd.Timestamp(end).tzinfo is None else pd.Timestamp(end).tz_convert("UTC").tz_localize(None)

        for file_path in self._candidate_files(symbol):
            dataframe = pd.read_csv(file_path)
            if dataframe.empty:
                continue
            if "symbol" not in dataframe.columns:
                continue

            for row in dataframe.to_dict(orient="records"):
                if str(row.get("symbol", "")).upper() != symbol:
                    continue
                row = dict(row)
                row.setdefault("interval", interval)
                row["symbol"] = symbol
                normalized = validate_candle(row)
                ts = normalized["timestamp"]
                if start_dt is not None and ts < pd.Timestamp(start).tz_localize(None).to_pydatetime():
                    continue
                if end_dt is not None and ts > pd.Timestamp(end).tz_localize(None).to_pydatetime():
                    continue
                rows.append(normalized)

        rows.sort(key=lambda item: item["timestamp"])
        return rows

    def fetch_latest_candle(self, symbol: str, interval: str = "1min") -> Optional[dict]:
        candles = self.fetch_candles(symbol, interval=interval)
        return candles[-1] if candles else None


__all__ = ["CSVDataProvider"]
