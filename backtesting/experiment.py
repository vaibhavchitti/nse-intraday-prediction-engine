from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

from backtesting.walk_forward import walk_forward_backtest
from evaluation.reporting import run_research_pipeline
from models.baseline import AlwaysFlatBaseline, MomentumBaseline, PriceTrendBaseline


def _resolve_predictor(model):
    if hasattr(model, "predict"):
        return model.predict
    if callable(model):
        return model
    raise TypeError("Each model must be either a predictor object with .predict() or a callable")


def compare_models(
    frame: pd.DataFrame | dict[str, pd.DataFrame],
    models: dict[str, object] | None = None,
    *,
    horizon_minutes: int = 5,
    train_window: int = 6,
    test_window: int = 3,
) -> dict:
    """Compare multiple predictors using one dataset or a dict of symbol->frame batches."""
    if models is None:
        models = {
            "always_flat": AlwaysFlatBaseline(),
            "price_trend": PriceTrendBaseline(),
            "momentum": MomentumBaseline(),
        }

    if not isinstance(models, dict):
        raise TypeError("models must be a dict mapping names to predictor objects")

    if isinstance(frame, dict):
        symbol_frames = {symbol: df for symbol, df in frame.items() if isinstance(df, pd.DataFrame)}
        if not symbol_frames:
            raise ValueError("frame dict must contain pandas DataFrames keyed by symbol")
    else:
        symbol_frames = {"__all__": frame}

    ranked = []
    per_symbol = {}

    for symbol, symbol_frame in symbol_frames.items():
        per_symbol[symbol] = {}
        for model_name, model in models.items():
            predictor = _resolve_predictor(model)
            result = walk_forward_backtest(
                symbol_frame,
                horizon_minutes=horizon_minutes,
                train_window=train_window,
                test_window=test_window,
                predictor=predictor,
            )
            per_symbol[symbol][model_name] = {
                "accuracy": result["metrics"]["accuracy"],
                "balanced_accuracy": result["metrics"].get("balanced_accuracy", 0.0),
                "n_samples": result["metrics"]["n_samples"],
                "coverage": result["coverage"],
            }

    for model_name, model in models.items():
        entries = [per_symbol[symbol][model_name] for symbol in symbol_frames]
        if not entries:
            continue

        accuracy = sum(entry["accuracy"] for entry in entries) / len(entries)
        balanced_accuracy = sum(entry["balanced_accuracy"] for entry in entries) / len(entries)
        n_samples = sum(entry["n_samples"] for entry in entries)
        coverage = sum(entry["coverage"] for entry in entries) / len(entries)
        ranked.append(
            {
                "model_name": model_name,
                "accuracy": accuracy,
                "balanced_accuracy": balanced_accuracy,
                "n_samples": n_samples,
                "coverage": coverage,
            }
        )

    ranked.sort(key=lambda row: (-row["accuracy"], -row["balanced_accuracy"], -row["n_samples"]))
    best_model = ranked[0] if ranked else None
    return {
        "n_models": len(ranked),
        "ranked_results": ranked,
        "best_model": best_model,
        "by_symbol": per_symbol,
    }


def run_research_pass(
    frame: pd.DataFrame | dict[str, pd.DataFrame],
    models: dict[str, object] | None = None,
    *,
    horizon_minutes: int = 5,
    train_window: int = 6,
    test_window: int = 3,
    output_path: str | Path | None = None,
) -> dict:
    """Compute a model comparison and persist the resulting research evidence bundle."""
    comparison = compare_models(
        frame,
        models=models,
        horizon_minutes=horizon_minutes,
        train_window=train_window,
        test_window=test_window,
    )
    payload = run_research_pipeline(comparison, output_path=output_path)
    return payload
