from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from data.validation import CandleValidationError


class DataProvider(ABC):
    """Common interface for all data providers used in the engine."""

    @abstractmethod
    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1min",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> list[dict]:
        """Return a list of candle dictionaries with standard OHLCV fields."""

    @abstractmethod
    def fetch_latest_candle(self, symbol: str, interval: str = "1min") -> Optional[dict]:
        """Return the most recent completed candle or None if unavailable."""


class ProviderError(RuntimeError):
    """Raised when a provider encounters a data or access problem."""


__all__ = ["DataProvider", "ProviderError", "CandleValidationError"]
