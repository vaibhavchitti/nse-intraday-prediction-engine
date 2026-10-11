from __future__ import annotations

import pandas as pd


def classify_breakout_signal(frame: pd.DataFrame, opening_range_minutes: int = 15) -> str:
    """Return UP/DOWN/FLAT for an opening-range breakout signal."""
    if frame.empty:
        return "FLAT"

    df = frame.copy().sort_values("timestamp").reset_index(drop=True)
    if len(df) < opening_range_minutes + 1:
        return "FLAT"

    opening = df.iloc[:opening_range_minutes]
    range_high = opening["high"].max()
    range_low = opening["low"].min()
    current = df.iloc[-1]
    prior = df.iloc[-2]

    bullish = current["close"] > range_high and current["close"] > prior["close"]
    bearish = current["close"] < range_low and current["close"] < prior["close"]

    if bullish:
        return "UP"
    if bearish:
        return "DOWN"
    return "FLAT"


class OpeningRangeBreakoutStrategy:
    """Prototype ORB evaluator with a basic reward-to-risk check."""

    def __init__(self, opening_range_minutes: int = 15, stop_loss_pct: float = 0.01, target_pct: float = 0.02):
        self.opening_range_minutes = opening_range_minutes
        self.stop_loss_pct = stop_loss_pct
        self.target_pct = target_pct

    def evaluate(self, frame: pd.DataFrame) -> dict:
        signal = classify_breakout_signal(frame, self.opening_range_minutes)
        reward_to_risk = self.target_pct / max(self.stop_loss_pct, 1e-6)
        return {
            "signal": signal,
            "reward_to_risk": reward_to_risk,
            "stop_loss_pct": self.stop_loss_pct,
            "target_pct": self.target_pct,
        }
