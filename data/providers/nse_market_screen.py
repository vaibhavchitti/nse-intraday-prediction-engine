from __future__ import annotations

import json
import urllib.request
from typing import Any


class NSEMarketScreenProvider:
    """Public NSE market-screen provider for exchange-wide momentum and volume rankings."""

    def __init__(self, base_url: str = "https://www.nseindia.com"):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
        }

    def _fetch_json(self, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        request = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch_market_screen(self) -> list[dict[str, Any]]:
        payload = self._fetch_json("/api/market-data-pre-open?key=ALL")
        records: list[dict[str, Any]] = []
        for item in payload.get("data", []):
            metadata = item.get("metadata") or {}
            symbol = (metadata.get("symbol") or "").strip().upper()
            if not symbol:
                continue

            records.append(
                {
                    "symbol": symbol,
                    "last_price": float(metadata.get("lastPrice") or 0.0),
                    "change": float(metadata.get("change") or 0.0),
                    "p_change": float(metadata.get("pChange") or 0.0),
                    "previous_close": float(metadata.get("previousClose") or 0.0),
                    "volume": float(metadata.get("finalQuantity") or 0.0),
                    "turnover": float(metadata.get("totalTurnover") or 0.0),
                    "market_cap": metadata.get("marketCap"),
                    "year_high": metadata.get("yearHigh"),
                    "year_low": metadata.get("yearLow"),
                    "iep": metadata.get("iep"),
                    "market_status": payload.get("marketStatus"),
                    "timestamp": payload.get("timestamp"),
                }
            )
        return records


__all__ = ["NSEMarketScreenProvider"]
