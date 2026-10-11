from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from evaluation.outcome_validator import OutcomeValidator
from ledger.forecast_store import ForecastLedger, OutcomeStore


@pytest.fixture
def ledger_path(tmp_path):
    return tmp_path / "forecast_ledger.db"


def test_ledger_is_append_only_and_idempotent(ledger_path):
    ledger = ForecastLedger(str(ledger_path))

    first = ledger.append_prediction(
        symbol="RELIANCE",
        exchange="NSE",
        prediction_time="2024-01-02T09:15:00+05:30",
        reference_price=100.0,
        horizon_minutes=5,
        predicted_class="UP",
        probability={"UP": 0.6, "DOWN": 0.2, "FLAT": 0.2},
        model_version="baseline_v1",
        feature_snapshot="snapshot-1",
        data_quality_status="OK",
        forecast_id="fc-001",
    )
    second = ledger.append_prediction(
        symbol="RELIANCE",
        exchange="NSE",
        prediction_time="2024-01-02T09:15:00+05:30",
        reference_price=100.0,
        horizon_minutes=5,
        predicted_class="UP",
        probability={"UP": 0.6, "DOWN": 0.2, "FLAT": 0.2},
        model_version="baseline_v1",
        feature_snapshot="snapshot-1",
        data_quality_status="OK",
        forecast_id="fc-001",
    )

    assert first["forecast_id"] == second["forecast_id"]
    assert ledger.count() == 1

    with pytest.raises(ValueError):
        ledger.update_prediction_status("fc-001", "VALIDATED")


def test_outcome_validation_and_csv_export(ledger_path):
    ledger = ForecastLedger(str(ledger_path))
    store = OutcomeStore(str(ledger_path))

    forecast_id = ledger.append_prediction(
        symbol="RELIANCE",
        exchange="NSE",
        prediction_time="2024-01-02T09:15:00+05:30",
        reference_price=100.0,
        horizon_minutes=5,
        predicted_class="UP",
        probability={"UP": 0.7, "DOWN": 0.2, "FLAT": 0.1},
        model_version="baseline_v1",
        feature_snapshot="snapshot-2",
        data_quality_status="OK",
        forecast_id="fc-002",
    )["forecast_id"]

    validator = OutcomeValidator(ledger, store)
    outcome = validator.validate_matured_forecast(
        forecast_id=forecast_id,
        actual_price=101.0,
        validation_time="2024-01-02T09:20:00+05:30",
    )

    assert outcome["actual_return"] > 0
    assert outcome["correct"] is True
    assert outcome["outcome_class"] == "UP"

    export_path = ledger_path.parent / "forecast_export.csv"
    ledger.export_csv(export_path)
    exported = pd.read_csv(export_path)
    assert len(exported) >= 1
    assert "forecast_id" in exported.columns
