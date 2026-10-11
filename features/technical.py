from __future__ import annotations

import pandas as pd


def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Return a standard RSI series with NaN for warm-up periods."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def compute_technical_features(candles: pd.DataFrame) -> pd.DataFrame:
    """Compute the core trend and momentum features for a candle stream."""
    frame = candles.copy().sort_values("timestamp").reset_index(drop=True)
    if "close" not in frame.columns:
        raise ValueError("Technical features require a close column")

    frame["ema_9"] = frame["close"].ewm(span=9, adjust=False).mean()
    frame["ema_20"] = frame["close"].ewm(span=20, adjust=False).mean()
    frame["ema_50"] = frame["close"].ewm(span=50, adjust=False).mean()
    frame["rsi_14"] = compute_rsi(frame["close"], window=14)
    frame["trend_strength"] = (frame["close"] - frame["close"].shift(1)) / frame["close"].shift(1)
    return frame
