from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from config import get_settings
from data.providers.synthetic_provider import SyntheticDataProvider
from ledger.forecast_store import ForecastLedger


class ScanRunner:
    """Minimal one-minute scan orchestration for Codespaces and replayable, offline use."""

    def __init__(
        self,
        provider: Any | None = None,
        symbols: list[str] | None = None,
        db_path: str | Path | None = None,
        report_dir: str | Path | None = None,
    ):
        self.settings = get_settings()
        self.provider = provider or SyntheticDataProvider(seed=self.settings.synthetic_seed)
        self.symbols = symbols or self.settings.universe
        self.db_path = str(db_path or "data/scan_ledger.db")
        self.report_dir = Path(report_dir) if report_dir is not None else None
        self.lock = threading.Lock()
        self._scan_counter = 0

    def acquire_lock(self) -> bool:
        return self.lock.acquire(blocking=False)

    def release_lock(self) -> None:
        try:
            self.lock.release()
        except RuntimeError:
            pass

    def run_once(self) -> dict[str, Any]:
        if not self.acquire_lock():
            return {
                "status": "SKIPPED_OVERLAP",
                "symbols_attempted": 0,
                "successful_fetches": 0,
                "forecasts_issued": 0,
                "outcomes_validated": 0,
                "errors": ["overlapping scan skipped"],
            }

        try:
            start = datetime.now()
            attempts = 0
            successful = 0
            errors: list[str] = []
            ledger = ForecastLedger(self.db_path)

            for symbol in self.symbols:
                attempts += 1
                try:
                    candles = self.provider.fetch_candles(symbol, interval="1min")
                    if candles:
                        successful += 1
                except Exception as exc:  # pragma: no cover - safety path
                    errors.append(f"{symbol}: {str(exc)}")

            self._scan_counter += 1
            result = {
                "status": "OK" if successful else "PARTIAL",
                "scan_id": f"scan-{self._scan_counter}",
                "started_at": start.isoformat(),
                "finished_at": datetime.now().isoformat(),
                "symbols_attempted": attempts,
                "successful_fetches": successful,
                "forecasts_issued": max(0, successful),
                "outcomes_validated": 0,
                "errors": errors,
                "ledger_path": self.db_path,
                "forecast_count": ledger.count(),
            }

            if self.report_dir is not None:
                self.report_dir.mkdir(parents=True, exist_ok=True)
                report_path = self.report_dir / "scan_report.json"
                report_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
                result["report_path"] = str(report_path)

            return result
        finally:
            self.release_lock()

    def run_loop(self, *, sleep_seconds: int = 60) -> list[dict]:
        results: list[dict] = []
        while True:
            results.append(self.run_once())
            if sleep_seconds > 0:
                import time
                time.sleep(sleep_seconds)


__all__ = ["ScanRunner"]
