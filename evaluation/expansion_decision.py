from __future__ import annotations

from pathlib import Path

from evaluation.reporting import build_research_report, export_research_report, rank_symbol_candidates, render_research_brief


def run_expansion_decision_pipeline(
    comparison: dict,
    *,
    live_data_available: bool,
    provider_is_free: bool,
    current_universe_size: int,
    successful_fetch_rate: float,
    min_symbol_accuracy: float = 0.65,
    min_coverage: float = 0.8,
    output_path: str | Path | None = None,
) -> dict:
    """Combine model evidence and a conservative watchlist decision into one exportable research bundle."""
    report = build_research_report(comparison)
    ranked_candidates = rank_symbol_candidates(comparison)
    decision = decide_watchlist_expansion(
        ranked_candidates,
        live_data_available=live_data_available,
        provider_is_free=provider_is_free,
        current_universe_size=current_universe_size,
        successful_fetch_rate=successful_fetch_rate,
        min_symbol_accuracy=min_symbol_accuracy,
        min_coverage=min_coverage,
    )

    bundle = {
        "report": report,
        "watchlist_decision": decision,
        "research_brief": render_research_brief(report),
        "decision_brief": decision["recommendation"],
    }

    persisted = {}
    if output_path is not None:
        persisted = export_research_report(bundle, output_path)
        bundle["path"] = persisted.get("output_path")
        bundle["bytes_written"] = persisted.get("bytes_written")
    else:
        bundle["path"] = None
        bundle["bytes_written"] = None

    return bundle


class ExpansionDecisionAnalyzer:
    """A conservative planner for whether to expand the universe beyond the initial list."""

    def evaluate(
        self,
        *,
        live_data_available: bool,
        provider_is_free: bool,
        current_universe_size: int,
        coverage: float,
        successful_fetch_rate: float,
    ) -> dict:
        should_expand = False
        recommendation = "Keep a limited universe until coverage and reliability are proven."

        if live_data_available and provider_is_free and current_universe_size < 50 and coverage >= 0.8 and successful_fetch_rate >= 0.9:
            should_expand = True
            recommendation = "Expand the universe cautiously after confirming coverage and reliability."
        elif not live_data_available:
            recommendation = "Stay on the limited offline-universe prototype until live data is verified."
        elif not provider_is_free:
            recommendation = "Do not expand the universe if the provider introduces paid rate limits or unreliable access."

        return {
            "should_expand": should_expand,
            "recommendation": recommendation,
            "coverage": float(coverage),
            "successful_fetch_rate": float(successful_fetch_rate),
            "current_universe_size": int(current_universe_size),
            "live_data_available": bool(live_data_available),
            "provider_is_free": bool(provider_is_free),
        }


def decide_watchlist_expansion(
    ranked_candidates: dict,
    *,
    live_data_available: bool,
    provider_is_free: bool,
    current_universe_size: int,
    successful_fetch_rate: float,
    min_symbol_accuracy: float = 0.65,
    min_coverage: float = 0.8,
) -> dict:
    """Use ranked candidate quality and a conservative provider gate to decide whether to expand the watchlist."""
    leaderboard = ranked_candidates.get("leaderboard", [])
    top_symbol = ranked_candidates.get("best_symbol")
    top_entry = leaderboard[0] if leaderboard else {}
    if top_symbol is None and top_entry:
        top_symbol = top_entry.get("symbol")

    top_accuracy = float(top_entry.get("accuracy", 0.0) if top_entry else 0.0)
    top_coverage = float(top_entry.get("coverage", 0.0) if top_entry else 0.0)
    coverage = max(top_coverage, 0.0)

    analyzer = ExpansionDecisionAnalyzer()
    base_decision = analyzer.evaluate(
        live_data_available=live_data_available,
        provider_is_free=provider_is_free,
        current_universe_size=current_universe_size,
        coverage=coverage,
        successful_fetch_rate=successful_fetch_rate,
    )

    has_strong_candidate = top_accuracy >= min_symbol_accuracy and coverage >= min_coverage
    should_expand = base_decision["should_expand"] and has_strong_candidate

    if should_expand:
        recommendation = (
            f"Expand the universe cautiously around {top_symbol} because it is a strong ranked candidate "
            f"with accuracy {top_accuracy:.2%} and coverage {coverage:.2%}."
        )
    else:
        recommendation = base_decision["recommendation"]
        if not has_strong_candidate:
            recommendation = (
                "Keep the universe limited until stronger ranked candidates emerge with at least "
                f"{min_symbol_accuracy:.0%} accuracy and {min_coverage:.0%} coverage."
            )

    return {
        "should_expand": bool(should_expand),
        "recommendation": recommendation,
        "top_symbol": top_symbol,
        "top_accuracy": top_accuracy,
        "coverage": coverage,
        "successful_fetch_rate": float(successful_fetch_rate),
        "current_universe_size": int(current_universe_size),
        "live_data_available": bool(live_data_available),
        "provider_is_free": bool(provider_is_free),
    }


__all__ = ["ExpansionDecisionAnalyzer", "decide_watchlist_expansion"]
