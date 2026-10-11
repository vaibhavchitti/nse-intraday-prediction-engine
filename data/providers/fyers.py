from __future__ import annotations

from typing import Optional

from data.providers.base import DataProvider, ProviderError
from data.validation import validate_candles


class FYERSDataProvider(DataProvider):
    """Thin FYERS integration that fails safely without credentials and never orders."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        base_url: str = "https://api.fyers.in",
        timeout_seconds: float = 10.0,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _require_credentials(self) -> None:
        if not self.api_key or not self.access_token:
            raise ValueError("FYERS API credentials are required for live market access")

    def _build_base_headers(self) -> dict:
        return {
            "api-key": self.api_key or "",
            "access-token": self.access_token or "",
            "Content-Type": "application/json",
        }

    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1min",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> list[dict]:
        self._require_credentials()
        try:
            import requests  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("The requests package is required for live FYERS calls") from exc
        raise NotImplementedError("Live FYERS integration requires verified provider docs and valid account permissions.")

    def fetch_latest_candle(self, symbol: str, interval: str = "1min") -> Optional[dict]:
        self._require_credentials()
        try:
            import requests  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("The requests package is required for live FYERS calls") from exc
        raise NotImplementedError("Live FYERS integration requires verified provider docs and valid account permissions.")


__all__ = ["FYERSDataProvider"]
