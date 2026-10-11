from __future__ import annotations

import pandas as pd
import pytest

from backtesting.walk_forward import walk_forward_backtest
from evaluation.metrics import evaluate_predictions
from features.price_action import compute_price_action_features
from features.technical import compute_technical_features
from features.volume import compute_volume_features
from models.baseline import AlwaysFlatBaseline, MomentumBaseline, PriceTrendBaseline


@pytest.fixture
def sample_candles_df():
    rows = []
    start = pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata")
    price = 100.0
    for minute in range(30):
        open_price = price
        close_price = open_price + (minute % 5 - 2) * 0.6
        high = max(open_price, close_price) + 0.8
        low = min(open_price, close_price) - 0.8
        volume = 1200 + minute * 50
        rows.append(
            {
                "symbol": "RELIANCE",
                "timestamp": start + pd.Timedelta(minutes=minute),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close_price, 2),
                "volume": volume,
            }
        )
        price = close_price
    return pd.DataFrame(rows)


def test_compute_feature_blocks(sample_candles_df):
    price_features = compute_price_action_features(sample_candles_df, horizons=[1, 3, 5])
    technical_features = compute_technical_features(sample_candles_df)
    volume_features = compute_volume_features(sample_candles_df)

    assert {"ret_1", "ret_3", "ret_5"}.issubset(price_features.columns)
    assert {"ema_9", "ema_20", "rsi_14"}.issubset(technical_features.columns)
    assert {"relative_volume", "volume_zscore"}.issubset(volume_features.columns)


def test_baselines_predict_class_labels():
    baseline = AlwaysFlatBaseline()
    assert baseline.predict([0.1, 0.2, 0.3]) == "FLAT"

    trend = PriceTrendBaseline()
    preds = trend.predict([0.01, 0.02, 0.03, 0.04, 0.05])
    assert preds in {"UP", "DOWN", "FLAT"}

    momentum = MomentumBaseline()
    assert momentum.predict([0.02, 0.03, 0.04, 0.06, 0.08]) == "UP"


def test_evaluation_metrics_and_walk_forward_backtest():
    metrics = evaluate_predictions(["UP", "DOWN", "UP", "FLAT"], ["UP", "DOWN", "FLAT", "FLAT"])
    assert metrics["accuracy"] >= 0.5
    assert metrics["confusion"]["UP"]["UP"] >= 1

    frame = pd.DataFrame(
        {
            "symbol": ["RELIANCE"] * 12,
            "timestamp": pd.date_range("2024-01-02 09:15:00", periods=12, freq="min", tz="Asia/Kolkata"),
            "close": [100.0, 100.4, 100.8, 101.2, 101.5, 101.9, 101.7, 101.6, 101.8, 101.9, 102.2, 102.5],
            "volume": [1200] * 12,
        }
    )

    result = walk_forward_backtest(frame, horizon_minutes=5, train_window=6, test_window=3)
    assert result["total_forecasts"] > 0
    assert set(result["metrics"].keys()) >= {"accuracy", "coverage", "n_samples"}
