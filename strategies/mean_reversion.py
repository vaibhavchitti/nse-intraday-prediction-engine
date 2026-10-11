from __future__ import annotations

import pandas as pd


class MeanReversionStrategy:
    """Simple range-bound mean-reversion candidate using distance from recent mean."""

    def evaluate(self, frame: pd.DataFrame) -> dict:
        if frame.empty:
            return {"signal": "FLAT", "score": 0.0}

        df = frame.copy().sort_values("timestamp").reset_index(drop=True)
        recent = df.tail(10)
        mean_price = recent["close"].mean()
        last_price = recent["close"].iloc[-1]
        spread = (last_price - mean_price) / mean_price

        if spread > 0.01:
            signal = "DOWN"
        elif spread < -0.01:
            signal = "UP"
        else:
            signal = "FLAT"

        return {"signal": signal, "score": float(spread)}
