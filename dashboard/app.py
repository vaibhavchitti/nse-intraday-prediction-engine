from __future__ import annotations

from typing import Any

import pandas as pd


def build_dashboard_pipeline_state(
    data: pd.DataFrame | None,
    *,
    scan_result: dict | None = None,
    report: dict | None = None,
    forecasts: list[dict] | None = None,
    metrics: dict | None = None,
    market_context: dict | None = None,
) -> dict[str, Any]:
    """Combine the raw dashboard state with scan and research evidence into one displayable state."""
    state = build_dashboard_state(data, forecasts=forecasts, metrics=metrics, market_context=market_context)
    if state["status"] == "NO_DATA":
        return state

    state["scan"] = scan_result or {}
    state["report"] = report or {}
    return state


def build_empty_dashboard_state() -> dict[str, Any]:
    return {
        "status": "NO_DATA",
        "market_regime": "UNKNOWN",
        "last_scan": None,
        "forecasts": [],
        "metrics": {},
        "market_context": {},
    }


def build_dashboard_state(
    data: pd.DataFrame | None,
    forecasts: list[dict] | None = None,
    metrics: dict | None = None,
    market_context: dict | None = None,
) -> dict[str, Any]:
    if data is None or data.empty:
        return build_empty_dashboard_state()

    state = {
        "status": "READY",
        "market_regime": (market_context or {}).get("market_regime", "UNKNOWN"),
        "last_scan": data["timestamp"].max().isoformat() if "timestamp" in data.columns else None,
        "forecasts": forecasts or [],
        "metrics": metrics or {},
        "market_context": market_context or {},
    }
    return state
