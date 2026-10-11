from __future__ import annotations

import pandas as pd

from dashboard.app import build_dashboard_state, build_empty_dashboard_state, build_dashboard_pipeline_state


def test_dashboard_builds_empty_state():
    state = build_empty_dashboard_state()
    assert state["status"] == "NO_DATA"
    assert state["forecasts"] == []


def test_dashboard_builds_nonempty_state():
    frame = pd.DataFrame(
        [
            {
                "symbol": "RELIANCE",
                "timestamp": pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata"),
                "close": 101.0,
                "volume": 1500,
            },
            {
                "symbol": "RELIANCE",
                "timestamp": pd.Timestamp("2024-01-02 09:16:00", tz="Asia/Kolkata"),
                "close": 101.8,
                "volume": 1600,
            },
        ]
    )
    state = build_dashboard_state(frame, forecasts=[{"symbol": "RELIANCE", "predicted_class": "UP", "horizon_minutes": 5}], metrics={"accuracy": 0.6, "coverage": 0.8})

    assert state["status"] == "READY"
    assert state["metrics"]["accuracy"] == 0.6
    assert state["forecasts"][0]["symbol"] == "RELIANCE"


def test_dashboard_pipeline_state_merges_scan_and_report_evidence():
    frame = pd.DataFrame(
        [
            {
                "symbol": "RELIANCE",
                "timestamp": pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata"),
                "close": 101.0,
                "volume": 1500,
            },
            {
                "symbol": "RELIANCE",
                "timestamp": pd.Timestamp("2024-01-02 09:16:00", tz="Asia/Kolkata"),
                "close": 101.8,
                "volume": 1600,
            },
        ]
    )

    state = build_dashboard_pipeline_state(
        frame,
        scan_result={"status": "OK", "successful_fetches": 2, "forecast_count": 2},
        report={"model_summary": {"winner": "trend", "winner_accuracy": 0.72}, "next_action": "expand_watchlist"},
        metrics={"accuracy": 0.72, "coverage": 0.95},
    )

    assert state["status"] == "READY"
    assert state["scan"]["status"] == "OK"
    assert state["report"]["model_summary"]["winner"] == "trend"
    assert state["metrics"]["accuracy"] == 0.72
