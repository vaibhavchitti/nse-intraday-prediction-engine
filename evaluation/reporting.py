from __future__ import annotations

import json
from pathlib import Path


def run_research_pipeline(comparison: dict, *, output_path: str | Path | None = None) -> dict:
    """Build, render, and optionally persist a complete evidence report for a research pass."""
    report = build_research_report(comparison)
    brief = render_research_brief(report)

    persisted = {}
    if output_path is not None:
        persisted = export_research_report(report, output_path)

    result = {
        "report": report,
        "brief": brief,
        "path": persisted.get("output_path"),
        "bytes_written": persisted.get("bytes_written"),
    }
    return result


def export_research_report(report: dict, output_path: str | Path) -> dict:
    """Persist a research report dictionary to JSON and return the saved metadata."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "output_path": str(path),
        "bytes_written": path.stat().st_size,
    }


def rank_symbol_candidates(comparison: dict) -> dict:
    """Rank symbols by their best model accuracy for a watchlist research pass."""
    by_symbol = comparison.get("by_symbol", {})
    if not by_symbol:
        return {
            "best_symbol": None,
            "candidate_count": 0,
            "leaderboard": [],
        }

    leaderboard = []
    for symbol, model_scores in by_symbol.items():
        best_model = None
        best_accuracy = -1.0
        best_coverage = 0.0

        for model_name, metrics in model_scores.items():
            accuracy = float(metrics.get("accuracy", 0.0))
            coverage = float(metrics.get("coverage", 0.0))
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_model = model_name
                best_coverage = coverage

        leaderboard.append(
            {
                "symbol": symbol,
                "best_model": best_model,
                "accuracy": best_accuracy,
                "coverage": best_coverage,
                "model_count": len(model_scores),
            }
        )

    leaderboard.sort(key=lambda row: (-row["accuracy"], -row["coverage"], row["symbol"]))
    return {
        "best_symbol": leaderboard[0]["symbol"] if leaderboard else None,
        "candidate_count": len(leaderboard),
        "leaderboard": leaderboard,
    }


def build_research_report(comparison: dict, *, min_accuracy: float = 0.65, min_coverage: float = 0.8) -> dict:
    """Build a single evidence-based report from model rankings and symbol-level evidence."""
    model_summary = summarize_experiment(comparison)
    symbol_ranking = rank_symbol_candidates(comparison)

    top_symbol = symbol_ranking.get("best_symbol")
    top_accuracy = 0.0
    if symbol_ranking.get("leaderboard"):
        top_accuracy = float(symbol_ranking["leaderboard"][0].get("accuracy", 0.0))

    if top_symbol and top_accuracy >= min_accuracy and model_summary.get("winner_accuracy", 0.0) >= min_accuracy:
        recommendation = (
            f"Strong evidence supports continued research around {top_symbol}; "
            f"the best model is {model_summary.get('winner')} with accuracy {model_summary.get('winner_accuracy', 0.0):.2%}."
        )
        next_action = "expand_watchlist"
    else:
        recommendation = (
            "Evidence is still limited; keep the universe focused and collect more out-of-sample validation before expansion."
        )
        next_action = "stay_limited"

    return {
        "model_summary": model_summary,
        "symbol_ranking": symbol_ranking,
        "recommendation": recommendation,
        "next_action": next_action,
    }


def render_research_brief(report: dict) -> str:
    """Render an evidence-based human-readable brief from the structured report dictionary."""
    model_summary = report.get("model_summary", {})
    symbol_ranking = report.get("symbol_ranking", {})
    recommendation = report.get("recommendation", "No recommendation available.")
    next_action = report.get("next_action", "stay_limited")

    winner = model_summary.get("winner", "unknown")
    winner_accuracy = model_summary.get("winner_accuracy", 0.0)
    best_symbol = symbol_ranking.get("best_symbol", "unknown")
    leaderboard = symbol_ranking.get("leaderboard", [])

    lines = [
        "Research brief",
        "---------------",
        f"Winner: {winner} ({winner_accuracy:.2%})",
        f"Top symbol: {best_symbol}",
    ]

    if leaderboard:
        lines.append("Top symbols:")
        for row in leaderboard[:3]:
            symbol = row.get("symbol", "unknown")
            accuracy = row.get("accuracy", 0.0)
            model_name = row.get("best_model", "unknown")
            lines.append(f"- {symbol}: {model_name} model at {float(accuracy):.2%}")

    lines.append(f"Recommendation: {recommendation}")
    lines.append(f"Next action: {next_action}")
    return "\n".join(lines)


def summarize_experiment(comparison: dict) -> dict:
    """Convert a ranked comparison payload into a concise research summary."""
    ranked = list(comparison.get("ranked_results", []))
    if not ranked:
        return {
            "winner": None,
            "winner_accuracy": 0.0,
            "n_models": 0,
            "leaderboard": [],
            "best_model_beat_baseline": False,
            "baseline_model": None,
            "baseline_accuracy": 0.0,
            "coverage": 0.0,
            "n_samples": 0,
            "research_note": "No model comparison data was available.",
        }

    ranked_rows = [
        {
            "rank": idx + 1,
            "model_name": row.get("model_name", f"model_{idx + 1}"),
            "accuracy": float(row.get("accuracy", 0.0)),
            "balanced_accuracy": float(row.get("balanced_accuracy", 0.0)),
            "n_samples": int(row.get("n_samples", 0)),
            "coverage": float(row.get("coverage", 0.0)),
        }
        for idx, row in enumerate(ranked)
    ]

    best = comparison.get("best_model") or ranked_rows[0]
    winner = str(best.get("model_name", ranked_rows[0]["model_name"]))
    winner_accuracy = float(best.get("accuracy", ranked_rows[0]["accuracy"]))
    baseline = ranked_rows[-1]
    best_model_beat_baseline = winner_accuracy > float(baseline["accuracy"])

    return {
        "winner": winner,
        "winner_accuracy": winner_accuracy,
        "n_models": int(comparison.get("n_models", len(ranked_rows))),
        "leaderboard": ranked_rows,
        "best_model_beat_baseline": bool(best_model_beat_baseline),
        "baseline_model": baseline["model_name"],
        "baseline_accuracy": float(baseline["accuracy"]),
        "coverage": float(best.get("coverage", ranked_rows[0]["coverage"])),
        "n_samples": int(best.get("n_samples", ranked_rows[0]["n_samples"])),
        "research_note": (
            f"Winner: {winner} with accuracy {winner_accuracy:.2%}. "
            f"Baseline model {baseline['model_name']} sits at {baseline['accuracy']:.2%}."
        ),
    }
