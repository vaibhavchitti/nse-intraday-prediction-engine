from __future__ import annotations

import pandas as pd

import dashboard.streamlit_app as streamlit_app
from config import get_settings
from dashboard.app import (
    build_dashboard_pipeline_state,
    build_dashboard_state,
    build_default_dashboard_data,
    build_empty_dashboard_state,
    build_market_dashboard,
    build_watchlist_table,
)
from dashboard.orb_screener import build_orb_watchlist
from dashboard.chart_screener import score_daily_chart


def test_dashboard_builds_empty_state():
    state = build_empty_dashboard_state()
    assert state["status"] == "NO_DATA"
    assert state["forecasts"] == []


def test_dashboard_builds_nonempty_state():
    frame = pd.DataFrame(
        [
            {
                "symbol": "RELIANCE",
                "timestamp": pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata"),
                "close": 101.0,
                "volume": 1500,
            },
            {
                "symbol": "RELIANCE",
                "timestamp": pd.Timestamp("2024-01-02 09:16:00", tz="Asia/Kolkata"),
                "close": 101.8,
                "volume": 1600,
            },
        ]
    )
    state = build_dashboard_state(frame, forecasts=[{"symbol": "RELIANCE", "predicted_class": "UP", "horizon_minutes": 5}], metrics={"accuracy": 0.6, "coverage": 0.8})

    assert state["status"] == "READY"
    assert state["metrics"]["accuracy"] == 0.6
    assert state["forecasts"][0]["symbol"] == "RELIANCE"


def test_dashboard_state_accepts_string_timestamps():
    timestamp = "2026-10-11T09:15:00+05:30"
    frame = pd.DataFrame([{"symbol": "RELIANCE", "timestamp": timestamp}])

    state = build_dashboard_state(frame)

    assert state["last_scan"] == pd.Timestamp(timestamp).isoformat()


def test_dashboard_pipeline_state_merges_scan_and_report_evidence():
    frame = pd.DataFrame(
        [
            {
                "symbol": "RELIANCE",
                "timestamp": pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata"),
                "close": 101.0,
                "volume": 1500,
            },
            {
                "symbol": "RELIANCE",
                "timestamp": pd.Timestamp("2024-01-02 09:16:00", tz="Asia/Kolkata"),
                "close": 101.8,
                "volume": 1600,
            },
        ]
    )

    state = build_dashboard_pipeline_state(
        frame,
        scan_result={"status": "OK", "successful_fetches": 2, "forecast_count": 2},
        report={"model_summary": {"winner": "trend", "winner_accuracy": 0.72}, "next_action": "expand_watchlist"},
        metrics={"accuracy": 0.72, "coverage": 0.95},
    )

    assert state["status"] == "READY"
    assert state["scan"]["status"] == "OK"
    assert state["report"]["model_summary"]["winner"] == "trend"
    assert state["metrics"]["accuracy"] == 0.72


def test_dashboard_can_build_default_synthetic_data():
    data, forecasts, metrics, market_context = build_default_dashboard_data()

    assert not data.empty
    assert len(data) >= 1
    assert "symbol" in data.columns
    assert len(forecasts) >= 1
    assert metrics["coverage"] > 0
    assert "market_regime" in market_context


def test_dashboard_can_build_filtered_watchlist():
    frame = pd.DataFrame(
        [
            {
                "symbol": "RELIANCE",
                "timestamp": pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata"),
                "close": 101.0,
                "volume": 1500,
            },
            {
                "symbol": "RELIANCE",
                "timestamp": pd.Timestamp("2024-01-02 09:16:00", tz="Asia/Kolkata"),
                "close": 101.8,
                "volume": 1600,
            },
            {
                "symbol": "TCS",
                "timestamp": pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata"),
                "close": 220.0,
                "volume": 1000,
            },
        ]
    )

    watchlist = build_watchlist_table(frame, selected_symbols=["RELIANCE"])

    assert list(watchlist["Symbol"]) == ["RELIANCE"]
    assert watchlist.iloc[0]["Last"] == 101.8
    assert watchlist.iloc[0]["Change %"] > 0


def test_dashboard_uses_full_configured_universe_by_default():
    universe = get_settings().universe
    data, forecasts, metrics, market_context = build_default_dashboard_data(use_yahoo_data=True)

    assert not data.empty
    assert "symbol" in data.columns
    assert len(forecasts) >= 3
    assert len(forecasts) == len({item["symbol"] for item in forecasts})
    assert market_context["provider"] == "yahoo-finance"
    assert market_context["symbol_count"] >= len(universe) * 0.5


def test_streamlit_main_prefers_live_nse_data_when_enabled(monkeypatch):
    nse_data = pd.DataFrame(
        [
            {"symbol": "TARAPUR", "last_price": 16.4, "p_change": 18.67, "volume": 53172, "change": 2.58},
            {"symbol": "IDEA", "last_price": 12.9, "p_change": 0.78, "volume": 2049262, "change": 0.10},
        ]
    )
    seen = {}

    monkeypatch.delenv("USE_NSE_LIVE_DATA", raising=False)
    monkeypatch.setattr(streamlit_app, "build_nse_market_dashboard", lambda: (nse_data, {"provider": "nse-market-screen"}))
    monkeypatch.setattr(streamlit_app, "build_default_dashboard_data", lambda: (_ for _ in ()).throw(AssertionError("default path should not run")))

    def fake_render_dashboard(**kwargs):
        seen["data"] = kwargs["data"]
        seen["market_context"] = kwargs["market_context"]

    monkeypatch.setattr(streamlit_app, "render_dashboard", fake_render_dashboard)
    monkeypatch.setattr(streamlit_app, "st", object())

    streamlit_app.main()

    assert len(seen["data"]) == 2
    assert seen["market_context"]["market_regime"] == "LIVE_NSE_MARKET"
    assert seen["data"]["symbol"].nunique() >= 2


def test_market_dashboard_builds_complete_signal_tables():
    frame = pd.DataFrame(
        [
            {"symbol": "RELIANCE", "timestamp": pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata"), "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 5000},
            {"symbol": "RELIANCE", "timestamp": pd.Timestamp("2024-01-02 09:16:00", tz="Asia/Kolkata"), "open": 100.5, "high": 102.0, "low": 100.0, "close": 101.8, "volume": 7000},
            {"symbol": "TCS", "timestamp": pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata"), "open": 200.0, "high": 201.0, "low": 198.0, "close": 199.0, "volume": 4000},
            {"symbol": "TCS", "timestamp": pd.Timestamp("2024-01-02 09:16:00", tz="Asia/Kolkata"), "open": 199.0, "high": 200.0, "low": 198.5, "close": 198.8, "volume": 3000},
            {"symbol": "INFY", "timestamp": pd.Timestamp("2024-01-02 09:15:00", tz="Asia/Kolkata"), "open": 150.0, "high": 152.0, "low": 149.0, "close": 149.2, "volume": 6500},
            {"symbol": "INFY", "timestamp": pd.Timestamp("2024-01-02 09:16:00", tz="Asia/Kolkata"), "open": 149.2, "high": 150.5, "low": 148.8, "close": 150.4, "volume": 9000},
        ]
    )

    dashboard = build_market_dashboard(frame)

    required = {
        "top_bullish",
        "top_bearish",
        "top_volume",
        "oversold",
        "overbought",
        "top_gainers",
        "top_losers",
        "top_vwap",
        "top_ema",
    }
    assert required.issubset(dashboard.keys())
    assert len(dashboard["top_bullish"]) >= 1
    assert len(dashboard["top_volume"]) >= 1
    assert len(dashboard["top_gainers"]) >= 1
    assert "Symbol" in dashboard["top_bullish"].columns
    assert "Symbol" in dashboard["top_volume"].columns


def test_orb_watchlist_scores_confirmed_setup_and_penalizes_missing_evidence():
    symbol = "RELIANCE"
    session_dates = pd.bdate_range("2026-09-21", periods=6)
    intraday_rows = []
    session_times = ["09:15", "09:20", "09:25", "09:30", "09:35", "09:40"]

    for session_date in session_dates[:-1]:
        for session_time in session_times:
            intraday_rows.append(
                {
                    "symbol": symbol,
                    "timestamp": f"{session_date.date()} {session_time}:00+05:30",
                    "open": 100.0,
                    "high": 100.5,
                    "low": 99.5,
                    "close": 100.0,
                    "volume": 10000,
                    "bid": 99.98,
                    "ask": 100.02,
                }
            )

    current_date = session_dates[-1]
    current_bars = [
        (100.0, 100.5, 99.5, 100.0),
        (100.0, 100.6, 99.6, 100.1),
        (100.1, 100.7, 99.7, 100.2),
        (100.8, 101.2, 100.8, 101.0),
        (101.0, 101.1, 100.65, 100.85),
        (100.9, 102.8, 100.9, 102.5),
    ]
    for session_time, (open_price, high, low, close) in zip(session_times, current_bars, strict=True):
        intraday_rows.append(
            {
                "symbol": symbol,
                "timestamp": f"{current_date.date()} {session_time}:00+05:30",
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": 30000,
                "bid": close - 0.02,
                "ask": close + 0.02,
            }
        )

    daily_dates = pd.bdate_range(end=session_dates[-2], periods=20)
    daily_data = pd.DataFrame(
        [{"symbol": symbol, "timestamp": date, "close": 500.0, "volume": 250000} for date in daily_dates]
    )
    reference_data = pd.DataFrame(
        [
            {
                "symbol": "NIFTY",
                "timestamp": f"{current_date.date()} {time}:00+05:30",
                "open": price - 0.1,
                "high": price + 0.1,
                "low": price - 0.2,
                "close": price,
                "volume": 1,
            }
            for time, price in zip(session_times, [100.0, 100.2, 100.3, 100.5, 100.7, 101.0], strict=True)
        ]
    )
    intraday_data = pd.DataFrame(intraday_rows)
    sector_data = {"Energy": reference_data}
    now = pd.Timestamp(f"{current_date.date()} 09:40:00+05:30")

    ranked = build_orb_watchlist(
        intraday_data,
        daily_data=daily_data,
        market_data=reference_data,
        sector_data=sector_data,
        sector_by_symbol={symbol: "Energy"},
        now=now,
    )
    incomplete = build_orb_watchlist(intraday_data, now=now)
    low_liquidity = build_orb_watchlist(
        intraday_data,
        daily_data=daily_data.assign(close=100.0),
        now=now,
    )

    assert ranked.iloc[0]["Symbol"] == symbol
    assert ranked.iloc[0]["ORB / Retest"] == "UP: FIRST RETEST HELD"
    assert ranked.iloc[0]["Last"] == 100.85
    assert bool(ranked.iloc[0]["ORB confirmed"])
    assert bool(ranked.iloc[0]["First retest held"])
    assert bool(ranked.iloc[0]["Market/sector aligned"])
    assert ranked.iloc[0]["Score"] > incomplete.iloc[0]["Score"]
    assert "daily liquidity" in incomplete.iloc[0]["Missing data"]
    assert "below 5 crore/day" in low_liquidity.iloc[0]["Rule failures"]
    assert incomplete.iloc[0]["Eligibility"] != "ELIGIBLE"


def test_daily_chart_scorecard_has_22_rules_and_five_bounded_components():
    dates = pd.bdate_range("2025-10-01", periods=260)
    close = [100 + index * 0.35 + (index % 7) * 0.1 for index in range(len(dates))]
    history = pd.DataFrame(
        [
            {
                "symbol": "RELIANCE",
                "timestamp": date,
                "open": price - 0.15,
                "high": price + 0.8,
                "low": price - 0.8,
                "close": price,
                "volume": 1_000_000 + (index % 5) * 50_000,
            }
            for index, (date, price) in enumerate(zip(dates, close, strict=True))
        ]
    )
    nifty_history = history.assign(symbol="NIFTY", close=[100 + index * 0.2 for index in range(len(dates))])

    result = score_daily_chart("RELIANCE", history, nifty_history)
    supertrend_rule = next(rule for rule in result["rules"] if rule["rule"] == "Close above SuperTrend(10, 3)")

    assert len(result["rules"]) == 22
    assert "warm-up" not in supertrend_rule["detail"]
    assert set(result["component_scores"]) == {"Trend", "Momentum", "Volume", "Volatility", "Support / resistance"}
    assert all(0 <= component_score <= 20 for component_score in result["component_scores"].values())
    assert result["score"] == sum(result["component_scores"].values())
    assert result["rating"] in {"strong bullish", "bullish", "neutral", "bearish", "strong bearish"}
    assert all({"component", "rule", "passed", "detail"}.issubset(rule) for rule in result["rules"])
