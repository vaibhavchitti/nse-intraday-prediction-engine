from __future__ import annotations

from evaluation.expansion_decision import (
    ExpansionDecisionAnalyzer,
    decide_watchlist_expansion,
    run_expansion_decision_pipeline,
)


def test_expansion_decision_is_conservative_without_live_coverage():
    analyzer = ExpansionDecisionAnalyzer()
    decision = analyzer.evaluate(
        live_data_available=False,
        provider_is_free=True,
        current_universe_size=10,
        coverage=0.45,
        successful_fetch_rate=0.9,
    )

    assert decision["should_expand"] is False
    assert "limited" in decision["recommendation"].lower()


def test_watchlist_expansion_uses_ranked_candidate_quality():
    decision = decide_watchlist_expansion(
        {
            "best_symbol": "RELIANCE",
            "leaderboard": [
                {"symbol": "RELIANCE", "best_model": "trend", "accuracy": 0.72, "coverage": 0.95},
                {"symbol": "TCS", "best_model": "flat", "accuracy": 0.55, "coverage": 0.86},
            ],
        },
        live_data_available=True,
        provider_is_free=True,
        current_universe_size=10,
        successful_fetch_rate=0.94,
    )

    assert decision["should_expand"] is True
    assert decision["top_symbol"] == "RELIANCE"
    assert "RELIANCE" in decision["recommendation"]


def test_run_expansion_decision_pipeline_aggregates_report_and_decision(tmp_path):
    comparison = {
        "n_models": 2,
        "best_model": {"model_name": "trend", "accuracy": 0.72, "coverage": 0.95},
        "ranked_results": [
            {"model_name": "trend", "accuracy": 0.72, "coverage": 0.95},
            {"model_name": "flat", "accuracy": 0.48, "coverage": 0.95},
        ],
        "by_symbol": {
            "RELIANCE": {"trend": {"accuracy": 0.72, "coverage": 0.95}, "flat": {"accuracy": 0.48, "coverage": 0.95}},
            "TCS": {"trend": {"accuracy": 0.61, "coverage": 0.90}, "flat": {"accuracy": 0.51, "coverage": 0.90}},
        },
    }

    output_path = tmp_path / "watchlist" / "expansion.json"
    result = run_expansion_decision_pipeline(
        comparison,
        live_data_available=True,
        provider_is_free=True,
        current_universe_size=10,
        successful_fetch_rate=0.94,
        output_path=output_path,
    )

    assert result["report"]["symbol_ranking"]["best_symbol"] == "RELIANCE"
    assert result["watchlist_decision"]["should_expand"] is True
    assert result["path"] == str(output_path)
    assert output_path.exists()
