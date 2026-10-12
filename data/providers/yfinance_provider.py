from __future__ import annotations

from typing import Optional

import pandas as pd

from data.providers.base import DataProvider, ProviderError
from data.validation import validate_candle


class YahooFinanceProvider(DataProvider):
    """Free historical data provider backed by Yahoo Finance for research use."""

    def __init__(self, symbol_suffix: str = ".NS", timeout_seconds: float = 30.0):
        self.symbol_suffix = symbol_suffix
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _require_yfinance():
        try:
            import yfinance as yf  # type: ignore
        except ModuleNotFoundError as exc:
            raise ProviderError(
                "yfinance is not installed. Install it with 'python -m pip install yfinance' "
                "to enable the free Yahoo Finance data path."
            ) from exc
        return yf

    @staticmethod
    def _normalize_interval(interval: str) -> str:
        text = (interval or "1m").strip().lower()
        mapping = {
            "1min": "1m",
            "5min": "5m",
            "15min": "15m",
            "30min": "30m",
            "60min": "60m",
            "1h": "1h",
            "daily": "1d",
            "1d": "1d",
            "1wk": "1wk",
            "1mo": "1mo",
        }
        return mapping.get(text, text)

    @staticmethod
    def _normalize_symbol(symbol: str, suffix: str) -> str:
        normalized = symbol.strip().upper()
        if not normalized:
            raise ProviderError("symbol is required")
        if normalized.endswith(suffix.upper()):
            return normalized
        return f"{normalized}{suffix}"

    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1min",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> list[dict]:
        yf = self._require_yfinance()
        ticker = yf.Ticker(self._normalize_symbol(symbol, self.symbol_suffix))

        history_kwargs = {
            "interval": self._normalize_interval(interval),
            "auto_adjust": True,
        }
        if start is not None:
            history_kwargs["start"] = start
        if end is not None:
            history_kwargs["end"] = end

        try:
            df = ticker.history(**history_kwargs)
        except Exception:
            return []
        if df is None or df.empty:
            return []

        records: list[dict] = []
        normalized_df = df.reset_index()
        for _, row in normalized_df.iterrows():
            timestamp_value = row.get("Datetime")
            if timestamp_value is None:
                timestamp_value = row.get("Date")
            if timestamp_value is None:
                timestamp_value = row.get("index")
            if timestamp_value is None:
                continue

            timestamp = pd.Timestamp(timestamp_value)
            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("UTC")

            candle = {
                "symbol": self._normalize_symbol(symbol, self.symbol_suffix).replace(self.symbol_suffix, "").upper(),
                "timestamp": timestamp.isoformat(),
                "open": float(row.get("Open", 0.0)),
                "high": float(row.get("High", 0.0)),
                "low": float(row.get("Low", 0.0)),
                "close": float(row.get("Close", 0.0)),
                "volume": float(row.get("Volume", 0.0)),
                "interval": self._normalize_interval(interval),
            }
            try:
                records.append(validate_candle(candle))
            except ValueError:
                continue

        records.sort(key=lambda item: item["timestamp"])
        return records

    def fetch_latest_candle(self, symbol: str, interval: str = "1min") -> Optional[dict]:
        candles = self.fetch_candles(symbol, interval=interval)
        return candles[-1] if candles else None

    def fetch_bid_ask(self, symbol: str) -> tuple[float | None, float | None]:
        """Return Yahoo's current bid/ask quote when available; missing quotes stay missing."""
        yf = self._require_yfinance()
        ticker = yf.Ticker(self._normalize_symbol(symbol, self.symbol_suffix))
        try:
            fast_info = ticker.fast_info
            bid = fast_info.get("bid")
            ask = fast_info.get("ask")
            return (float(bid) if bid is not None else None, float(ask) if ask is not None else None)
        except Exception:
            return None, None


__all__ = ["YahooFinanceProvider"]
