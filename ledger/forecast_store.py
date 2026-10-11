from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from shutil import copy2

import pandas as pd


class ForecastLedger:
    """Append-only SQLite ledger for immutable forecast records."""

    def __init__(self, db_path: str | Path = "forecast_ledger.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS forecasts (
                    forecast_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    prediction_time TEXT NOT NULL,
                    reference_price REAL NOT NULL,
                    horizon_minutes INTEGER NOT NULL,
                    predicted_class TEXT NOT NULL,
                    probability_json TEXT NOT NULL,
                    model_version TEXT,
                    feature_snapshot TEXT,
                    data_quality_status TEXT DEFAULT 'OK',
                    signal_explanation TEXT,
                    forecast_status TEXT DEFAULT 'PENDING',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def append_prediction(
        self,
        *,
        symbol: str,
        exchange: str,
        prediction_time: str,
        reference_price: float,
        horizon_minutes: int,
        predicted_class: str,
        probability: dict,
        model_version: str,
        feature_snapshot: str,
        data_quality_status: str = "OK",
        signal_explanation: str | None = None,
        forecast_id: str | None = None,
    ) -> dict:
        if forecast_id is None:
            forecast_id = f"{symbol}-{prediction_time}-{horizon_minutes}"

        probability_json = json.dumps(probability, sort_keys=True)

        with self.conn:
            row = self.conn.execute(
                """
                INSERT OR IGNORE INTO forecasts (
                    forecast_id, symbol, exchange, prediction_time, reference_price,
                    horizon_minutes, predicted_class, probability_json, model_version,
                    feature_snapshot, data_quality_status, signal_explanation, forecast_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
                """,
                (
                    forecast_id,
                    symbol.upper(),
                    exchange.upper(),
                    prediction_time,
                    float(reference_price),
                    int(horizon_minutes),
                    predicted_class.upper(),
                    probability_json,
                    model_version,
                    feature_snapshot,
                    data_quality_status,
                    signal_explanation,
                ),
            ).lastrowid

        return self.get_prediction(forecast_id)

    def get_prediction(self, forecast_id: str) -> dict:
        row = self.conn.execute(
            "SELECT * FROM forecasts WHERE forecast_id = ?",
            (forecast_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Forecast {forecast_id} not found")
        return dict(row)

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0])

    def list_predictions(self):
        rows = self.conn.execute("SELECT * FROM forecasts ORDER BY prediction_time").fetchall()
        return [dict(row) for row in rows]

    def export_csv(self, path: str | Path) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(self.list_predictions())
        df.to_csv(path, index=False)
        return str(path)

    def backup_database(self, backup_path: str | Path) -> str:
        backup_target = Path(backup_path)
        backup_target.parent.mkdir(parents=True, exist_ok=True)
        copy2(self.db_path, backup_target)
        return str(backup_target)

    def update_prediction_status(self, forecast_id: str, status: str) -> None:
        raise ValueError("Forecast ledger is append-only and does not allow status overwrites.")


class OutcomeStore:
    """Separate outcome table for validated forecast results."""

    def __init__(self, db_path: str | Path = "forecast_ledger.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    forecast_id TEXT NOT NULL UNIQUE,
                    outcome_class TEXT NOT NULL,
                    actual_return REAL NOT NULL,
                    actual_price REAL NOT NULL,
                    predicted_class TEXT NOT NULL,
                    correctness INTEGER NOT NULL,
                    validation_time TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def record_outcome(
        self,
        *,
        forecast_id: str,
        outcome_class: str,
        actual_return: float,
        actual_price: float,
        predicted_class: str,
        correctness: bool,
        validation_time: str,
        outcome_id: str | None = None,
    ) -> dict:
        if outcome_id is None:
            outcome_id = f"outcome-{forecast_id}"

        with self.conn:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO outcomes (
                    outcome_id, forecast_id, outcome_class, actual_return,
                    actual_price, predicted_class, correctness, validation_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome_id,
                    forecast_id,
                    outcome_class.upper(),
                    float(actual_return),
                    float(actual_price),
                    predicted_class.upper(),
                    int(bool(correctness)),
                    validation_time,
                ),
            )
        return self.get_outcome(forecast_id)

    def get_outcome(self, forecast_id: str) -> dict:
        row = self.conn.execute(
            "SELECT * FROM outcomes WHERE forecast_id = ?",
            (forecast_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Outcome for forecast {forecast_id} not found")
        return dict(row)

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0])

    def export_csv(self, path: str | Path) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(self.list_outcomes())
        df.to_csv(path, index=False)
        return str(path)

    def list_outcomes(self):
        rows = self.conn.execute("SELECT * FROM outcomes ORDER BY validation_time").fetchall()
        return [dict(row) for row in rows]

    def backup_database(self, backup_path: str | Path) -> str:
        backup_target = Path(backup_path)
        backup_target.parent.mkdir(parents=True, exist_ok=True)
        copy2(self.db_path, backup_target)
        return str(backup_target)


__all__ = ["ForecastLedger", "OutcomeStore"]
