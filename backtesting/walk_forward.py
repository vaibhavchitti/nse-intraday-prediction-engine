from __future__ import annotations

import pandas as pd

from evaluation.metrics import evaluate_predictions
from models.baseline import PriceTrendBaseline


def classify_return(value: float | None, *, positive_threshold: float = 0.002, negative_threshold: float = -0.002) -> str:
    if value is None or pd.isna(value):
        return "FLAT"
    if value > positive_threshold:
        return "UP"
    if value < negative_threshold:
        return "DOWN"
    return "FLAT"


def walk_forward_backtest(
    frame: pd.DataFrame,
    horizon_minutes: int = 5,
    train_window: int = 6,
    test_window: int = 3,
    predictor=None,
) -> dict:
    """Run a minimal walk-forward evaluation over a single time-ordered candle sequence."""
    df = frame.copy().sort_values("timestamp").reset_index(drop=True)
    if "close" not in df.columns:
        raise ValueError("Backtest input needs a close column")

    if predictor is None:
        predictor = PriceTrendBaseline().predict
    elif hasattr(predictor, "predict"):
        predictor = predictor.predict
    elif not callable(predictor):
        raise TypeError("predictor must be a callable or object exposing .predict()")

    actual_labels = []
    predicted_labels = []

    for index in range(len(df) - horizon_minutes):
        current_close = df["close"].iloc[index]
        future_close = df["close"].iloc[index + horizon_minutes]
        realized_return = (future_close / current_close) - 1.0
        actual_labels.append(classify_return(realized_return))

        start = max(0, index - train_window + 1)
        history = df["close"].iloc[start:index + 1].pct_change().dropna().tolist()
        predicted_labels.append(predictor(history))

    metrics = evaluate_predictions(actual_labels, predicted_labels)
    return {
        "total_forecasts": len(actual_labels),
        "coverage": len(actual_labels) / max(1, len(df)),
        "metrics": metrics,
    }
