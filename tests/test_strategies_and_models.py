from __future__ import annotations

import pandas as pd
import pytest

from strategies.orb import OpeningRangeBreakoutStrategy, classify_breakout_signal
from strategies.mean_reversion import MeanReversionStrategy


@pytest.fixture
def orb_frame():
    rows = []
    base = pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata")
    price = 100.0
    for minute in range(1, 31):
        close = price + (0.4 if minute % 3 == 0 else -0.2)
        rows.append(
            {
                "timestamp": base + pd.Timedelta(minutes=minute),
                "open": round(price, 2),
                "high": round(max(price, close) + 0.5, 2),
                "low": round(min(price, close) - 0.5, 2),
                "close": round(close, 2),
                "volume": 1500 + minute * 10,
            }
        )
        price = close
    return pd.DataFrame(rows)


def test_orb_signal_classification_and_strategy(orb_frame):
    signal = classify_breakout_signal(orb_frame, opening_range_minutes=15)
    assert signal in {"UP", "DOWN", "FLAT"}

    strategy = OpeningRangeBreakoutStrategy()
    decision = strategy.evaluate(orb_frame)
    assert decision["signal"] in {"UP", "DOWN", "FLAT"}
    assert "reward_to_risk" in decision


def test_mean_reversion_strategy_returns_reasonable_signal(orb_frame):
    strategy = MeanReversionStrategy()
    decision = strategy.evaluate(orb_frame)
    assert decision["signal"] in {"UP", "DOWN", "FLAT"}
