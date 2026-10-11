from __future__ import annotations

import pandas as pd


def compute_volume_features(candles: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Compute relative-volume and liquidity features for the candle stream."""
    frame = candles.copy().sort_values("timestamp").reset_index(drop=True)
    if "volume" not in frame.columns:
        raise ValueError("Volume features require a volume column")

    rolling_mean = frame["volume"].rolling(window=window, min_periods=1).mean()
    rolling_std = frame["volume"].rolling(window=window, min_periods=2).std().fillna(0)
    frame["relative_volume"] = frame["volume"] / rolling_mean.replace(0, pd.NA)
    frame["volume_zscore"] = (frame["volume"] - rolling_mean) / rolling_std.replace(0, pd.NA)
    frame["volume_zscore"] = frame["volume_zscore"].fillna(0.0)
    return frame
