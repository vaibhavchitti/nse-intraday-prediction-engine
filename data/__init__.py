from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Optional


class DataProvider(ABC):
    """Common interface for all data providers used in the engine.

    Implementations may provide synthetic, CSV, or live broker data. The
    provider contract is intentionally narrow so the rest of the project can be
    tested without depending on external credentials.
    """

    @abstractmethod
    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1min",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[dict]:
        """Return a list of candle dictionaries with standard OHLCV fields."""

    @abstractmethod
    def fetch_latest_candle(self, symbol: str, interval: str = "1min") -> Optional[dict]:
        """Return the most recent completed candle or None if unavailable."""


class ProviderError(RuntimeError):
    """Raised when a provider encounters a data or access problem."""


class DataValidationError(ValueError):
    """Raised when input candles are malformed or stale."""


__all__ = ["DataProvider", "ProviderError", "DataValidationError"]
