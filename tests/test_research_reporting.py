from __future__ import annotations

from evaluation.reporting import (
    build_research_report,
    export_research_report,
    rank_symbol_candidates,
    render_research_brief,
    run_research_pipeline,
    summarize_experiment,
)


def test_summarize_experiment_returns_clear_research_summary():
    comparison = {
        "n_models": 3,
        "best_model": {"model_name": "trend", "accuracy": 0.72, "n_samples": 40, "coverage": 0.94},
        "ranked_results": [
            {"model_name": "trend", "accuracy": 0.72, "n_samples": 40, "coverage": 0.94},
            {"model_name": "momentum", "accuracy": 0.61, "n_samples": 40, "coverage": 0.94},
            {"model_name": "flat", "accuracy": 0.50, "n_samples": 40, "coverage": 0.94},
        ],
    }

    summary = summarize_experiment(comparison)

    assert summary["winner"] == "trend"
    assert summary["winner_accuracy"] == 0.72
    assert summary["n_models"] == 3
    assert "leaderboard" in summary
    assert summary["leaderboard"][0]["model_name"] == "trend"
    assert "best_model_beat_baseline" in summary


def test_rank_symbol_candidates_returns_top_watchlist_candidates():
    comparison = {
        "n_models": 2,
        "by_symbol": {
            "RELIANCE": {"trend": {"accuracy": 0.72, "coverage": 0.95}, "flat": {"accuracy": 0.48, "coverage": 0.95}},
            "TCS": {"trend": {"accuracy": 0.61, "coverage": 0.92}, "flat": {"accuracy": 0.52, "coverage": 0.92}},
            "INFY": {"trend": {"accuracy": 0.67, "coverage": 0.90}, "flat": {"accuracy": 0.55, "coverage": 0.90}},
        }
    }

    ranked = rank_symbol_candidates(comparison)

    assert ranked["best_symbol"] == "RELIANCE"
    assert ranked["leaderboard"][0]["symbol"] == "RELIANCE"
    assert ranked["leaderboard"][0]["best_model"] == "trend"
    assert ranked["leaderboard"][0]["accuracy"] == 0.72


def test_build_research_report_aggregates_model_and_symbol_evidence():
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

    report = build_research_report(comparison)

    assert report["model_summary"]["winner"] == "trend"
    assert report["symbol_ranking"]["best_symbol"] == "RELIANCE"
    assert "recommendation" in report
    assert report["next_action"] in {"expand_watchlist", "stay_limited"}


def test_render_research_brief_returns_plain_text_summary():
    report = {
        "model_summary": {"winner": "trend", "winner_accuracy": 0.72},
        "symbol_ranking": {"best_symbol": "RELIANCE", "leaderboard": [{"symbol": "RELIANCE", "accuracy": 0.72}]},
        "recommendation": "Strong evidence supports continued research around RELIANCE.",
        "next_action": "expand_watchlist",
    }

    brief = render_research_brief(report)

    assert "trend" in brief.lower()
    assert "RELIANCE" in brief
    assert "expand_watchlist" in brief.lower()


def test_export_research_report_writes_json(tmp_path):
    report = {
        "model_summary": {"winner": "trend", "winner_accuracy": 0.72},
        "symbol_ranking": {"best_symbol": "RELIANCE", "leaderboard": [{"symbol": "RELIANCE", "accuracy": 0.72}]},
        "recommendation": "Strong evidence supports continued research around RELIANCE.",
        "next_action": "expand_watchlist",
    }

    output_path = tmp_path / "report.json"
    saved = export_research_report(report, output_path)

    assert saved["output_path"] == str(output_path)
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8")


def test_run_research_pipeline_return_and_persist_report(tmp_path):
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

    output_path = tmp_path / "research" / "report.json"
    result = run_research_pipeline(comparison, output_path=output_path)

    assert result["report"]["model_summary"]["winner"] == "trend"
    assert result["report"]["symbol_ranking"]["best_symbol"] == "RELIANCE"
    assert result["path"] == str(output_path)
    assert output_path.exists()
