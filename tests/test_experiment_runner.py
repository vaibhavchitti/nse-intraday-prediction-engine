from __future__ import annotations

import pandas as pd

from backtesting.experiment import compare_models, run_research_pass
from models.baseline import AlwaysFlatBaseline, MomentumBaseline, PriceTrendBaseline


def build_sample_frame():
    rows = []
    base = pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata")
    price = 100.0
    for minute in range(1, 41):
        close = price + (0.3 if minute % 4 == 0 else -0.15)
        rows.append(
            {
                "symbol": "RELIANCE",
                "timestamp": base + pd.Timedelta(minutes=minute),
                "open": round(price, 2),
                "high": round(max(price, close) + 0.4, 2),
                "low": round(min(price, close) - 0.4, 2),
                "close": round(close, 2),
                "volume": 1200 + minute * 10,
            }
        )
        price = close
    return pd.DataFrame(rows)


def test_compare_models_returns_ranked_summary():
    frame = build_sample_frame()
    comparison = compare_models(
        frame,
        models={
            "flat": AlwaysFlatBaseline(),
            "trend": PriceTrendBaseline(),
            "momentum": MomentumBaseline(),
        },
    )

    assert comparison["n_models"] == 3
    assert len(comparison["ranked_results"]) == 3
    assert all("accuracy" in row for row in comparison["ranked_results"])
    assert "best_model" in comparison
    assert comparison["best_model"]["model_name"] in {"flat", "trend", "momentum"}


def test_compare_models_supports_multi_symbol_universe():
    frames = {
        "RELIANCE": build_sample_frame(),
        "TCS": build_sample_frame(),
    }

    comparison = compare_models(
        frames,
        models={
            "flat": AlwaysFlatBaseline(),
            "trend": PriceTrendBaseline(),
        },
    )

    assert comparison["n_models"] == 2
    assert "by_symbol" in comparison
    assert set(comparison["by_symbol"].keys()) == {"RELIANCE", "TCS"}
    assert comparison["best_model"]["model_name"] in {"flat", "trend"}


def test_run_research_pass_builds_and_saves_research_bundle(tmp_path):
    frames = {
        "RELIANCE": build_sample_frame(),
        "TCS": build_sample_frame(),
    }
    output_path = tmp_path / "research" / "report.json"

    result = run_research_pass(
        frames,
        models={"flat": AlwaysFlatBaseline(), "trend": PriceTrendBaseline()},
        output_path=output_path,
    )

    assert result["report"]["model_summary"]["winner"] in {"flat", "trend"}
    assert result["path"] == str(output_path)
    assert output_path.exists()
