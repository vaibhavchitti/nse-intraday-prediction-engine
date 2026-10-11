from __future__ import annotations

import pandas as pd


def compute_price_action_features(candles: pd.DataFrame, horizons=(1, 3, 5, 10, 15)) -> pd.DataFrame:
    """Compute return-based price action features for the provided candle stream."""
    frame = candles.copy().sort_values("timestamp").reset_index(drop=True)
    if "close" not in frame.columns:
        raise ValueError("Price action features require a close column")

    for horizon in horizons:
        if horizon <= 0:
            continue
        future = frame["close"].shift(-horizon)
        frame[f"ret_{horizon}"] = (future / frame["close"]) - 1.0

    if {"open", "high", "low"}.issubset(frame.columns):
        frame["body_size"] = (frame["close"] - frame["open"]).abs()
        frame["total_range"] = (frame["high"] - frame["low"]).replace(0, pd.NA)
        frame["body_ratio"] = frame["body_size"] / frame["total_range"]
        frame["upper_wick"] = (frame["high"] - frame[["open", "close"]].max(axis=1)).clip(lower=0)
        frame["lower_wick"] = (frame[["open", "close"]].min(axis=1) - frame["low"]).clip(lower=0)
        frame["wick_ratio"] = (frame["upper_wick"] + frame["lower_wick"]) / frame["total_range"]
        frame["distance_from_open"] = (frame["close"] - frame["open"]) / frame["open"]

    return frame
