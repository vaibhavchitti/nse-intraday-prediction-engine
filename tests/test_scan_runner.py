from __future__ import annotations

import tempfile

from data.providers.synthetic_provider import SyntheticDataProvider
from scheduler.runner import ScanRunner


def test_scan_runner_runs_once_and_tracks_metrics():
    with tempfile.TemporaryDirectory() as tmp_dir:
        runner = ScanRunner(
            provider=SyntheticDataProvider(seed=7),
            symbols=["RELIANCE", "TCS"],
            db_path=f"{tmp_dir}/scan.db",
        )
        result = runner.run_once()

        assert result["status"] in {"OK", "PARTIAL"}
        assert result["symbols_attempted"] >= 1
        assert result["forecasts_issued"] >= 0
        assert result["errors"] == []


def test_scan_runner_rejects_overlap():
    runner = ScanRunner(provider=SyntheticDataProvider(seed=11), symbols=["RELIANCE"])
    assert runner.acquire_lock() is True
    assert runner.acquire_lock() is False
    runner.release_lock()


def test_scan_runner_can_save_report_artifact(tmp_path):
    runner = ScanRunner(
        provider=SyntheticDataProvider(seed=5),
        symbols=["RELIANCE", "TCS"],
        db_path=f"{tmp_path}/scan.db",
        report_dir=tmp_path / "reports",
    )

    result = runner.run_once()

    assert result["status"] in {"OK", "PARTIAL"}
    assert result["report_path"].endswith("scan_report.json")
    assert (tmp_path / "reports" / "scan_report.json").exists()
