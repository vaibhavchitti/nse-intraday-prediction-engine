from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - fallback for non-UI environments
    st = None

from dashboard.app import (
    build_dashboard_state,
    build_daily_chart_research_scorecard,
    build_default_dashboard_data,
    build_market_dashboard,
    build_nse_market_dashboard,
    build_orb_research_watchlist,
    build_watchlist_table,
)


def render_dashboard(data=None, forecasts=None, metrics=None, market_context=None):
    if st is None:
        return build_dashboard_state(data, forecasts=forecasts, metrics=metrics, market_context=market_context)

    state = build_dashboard_state(data, forecasts=forecasts, metrics=metrics, market_context=market_context)
    st.title("NSE Intraday Prediction Engine")
    st.caption("Research-only dashboard for historical, synthetic, and Yahoo Finance market scans.")

    if state["status"] == "NO_DATA":
        st.warning("No market data is available yet. Upload or replay historical data to populate the dashboard.")
        return state

    col1, col2, col3 = st.columns(3)
    col1.metric("Status", state["status"])
    col2.metric("Last scan", state["last_scan"] or "N/A")
    col3.metric("Accuracy", f"{float(metrics.get('accuracy', 0.0)):.2%}" if metrics else "N/A")

    coverage = float(metrics.get("coverage", 0.0)) if metrics else 0.0
    st.metric("Coverage", f"{coverage:.2%}")

    if market_context:
        st.subheader("Market context")
        st.json(market_context)

    st.subheader("5-minute ORB research watchlist")
    if st.button("Refresh ORB candidates", key="refresh_orb_candidates"):
        with st.spinner("Fetching recent candles, liquidity history, and market references..."):
            st.session_state["orb_watchlist"] = build_orb_research_watchlist()
    if "orb_watchlist" in st.session_state:
        orb_watchlist = st.session_state["orb_watchlist"]
        if orb_watchlist.empty:
            st.warning("No intraday candidate data is available. Check the Yahoo Finance connection and configured universe.")
        else:
            st.caption("Research score only; missing or stale inputs reduce eligibility. The thresholds are unvalidated and do not imply a profitable trade.")
            st.dataframe(orb_watchlist, use_container_width=True)
            symbols = orb_watchlist["Symbol"].astype(str).tolist()
            selected_symbol = st.selectbox("Candidate checklist", symbols, key="orb_checklist_symbol")
            candidate = orb_watchlist.loc[orb_watchlist["Symbol"].eq(selected_symbol)].iloc[0]
            direction = candidate["Direction"]
            is_bullish = direction == "UP"
            checklist = [
                (
                    "Price above rising VWAP" if is_bullish else "Price below falling VWAP",
                    bool(candidate["VWAP confirmed"]),
                ),
                (
                    "Completed 5-minute candle closes above today's opening-range high"
                    if is_bullish
                    else "Completed 5-minute candle closes below today's opening-range low",
                    bool(candidate["ORB confirmed"]),
                ),
                ("Relative volume >= 1.5x the time-of-day baseline", bool(candidate["Relative volume confirmed"])),
                ("First retest holds the breakout level", bool(candidate["First retest held"])),
                ("NIFTY and sector support the direction", bool(candidate["Market/sector aligned"])),
                ("Logical stop permits at least 1:2 reward-to-risk", bool(candidate["Risk/reward confirmed"])),
            ]
            confirmed_count = sum(confirmed for _, confirmed in checklist)
            st.markdown(f"**Intraday confirmation checklist: {confirmed_count}/6**")
            st.progress(confirmed_count / 6)
            for index, (label, confirmed) in enumerate(checklist):
                st.checkbox(label, value=confirmed, disabled=True, key=f"orb_checklist_{selected_symbol}_{index}")
    else:
        st.info("ORB candidates have not been scanned in this session.")

    st.subheader("Daily chart scorecard")
    if st.button("Refresh daily chart scores", key="refresh_daily_chart_scores"):
        with st.spinner("Fetching one year of daily candles and NIFTY history..."):
            summary, details = build_daily_chart_research_scorecard()
            st.session_state["daily_chart_summary"] = summary
            st.session_state["daily_chart_details"] = details
    if "daily_chart_summary" in st.session_state:
        daily_summary = st.session_state["daily_chart_summary"]
        daily_details = st.session_state["daily_chart_details"]
        if daily_summary.empty:
            st.warning("No daily chart history is available from Yahoo Finance for the configured universe.")
        else:
            st.caption("Latest-close checklist, not a forecast. Partial history causes unavailable long-lookback rules to fail.")
            st.dataframe(daily_summary, use_container_width=True)
            chart_symbol = st.selectbox("Chart rule details", daily_summary["Symbol"].tolist(), key="daily_chart_symbol")
            chart_result = daily_details[chart_symbol]
            st.metric("Chart rating", f"{chart_result['rating']} ({chart_result['score']:.0f}/100)")
            st.json({"component_scores": chart_result["component_scores"], "as_of": chart_result["as_of"], "data_status": chart_result["data_status"]})
            st.dataframe(pd.DataFrame(chart_result["rules"]), use_container_width=True)

    if data is not None and not data.empty:
        symbols = sorted({str(symbol).upper() for symbol in data["symbol"].dropna()}) if "symbol" in data.columns else []
        selected_symbols = st.sidebar.multiselect("Symbols", options=symbols, default=symbols)
        filtered_data = data[data["symbol"].astype(str).str.upper().isin(selected_symbols)] if "symbol" in data.columns and selected_symbols else data
        watchlist = build_watchlist_table(filtered_data, selected_symbols=selected_symbols)
        st.subheader("Watchlist")
        st.dataframe(watchlist, use_container_width=True)

        market_dashboard = build_market_dashboard(filtered_data)
        st.subheader("Top bullish")
        st.dataframe(market_dashboard["top_bullish"], use_container_width=True)
        st.subheader("Top bearish")
        st.dataframe(market_dashboard["top_bearish"], use_container_width=True)
        st.subheader("Top volume")
        st.dataframe(market_dashboard["top_volume"], use_container_width=True)
        st.subheader("Oversold")
        st.dataframe(market_dashboard["oversold"], use_container_width=True)
        st.subheader("Overbought")
        st.dataframe(market_dashboard["overbought"], use_container_width=True)
        st.subheader("Top gainers")
        st.dataframe(market_dashboard["top_gainers"], use_container_width=True)
        st.subheader("Top losers")
        st.dataframe(market_dashboard["top_losers"], use_container_width=True)
        st.subheader("Top VWAP")
        st.dataframe(market_dashboard["top_vwap"], use_container_width=True)
        st.subheader("Top EMA")
        st.dataframe(market_dashboard["top_ema"], use_container_width=True)

        if not filtered_data.empty and "timestamp" in filtered_data.columns:
            chart_data = filtered_data.sort_values("timestamp").copy()
            chart_data = chart_data.pivot_table(index="timestamp", columns="symbol", values="close", aggfunc="last")
            st.subheader("Price trend")
            st.line_chart(chart_data)

    if os.getenv("USE_NSE_LIVE_DATA", "1").lower() in {"1", "true", "yes", "y"}:
        nse_data, nse_meta = build_nse_market_dashboard()
        if not nse_data.empty:
            st.subheader("NSE live market screen")
            st.json(nse_meta)
            nse_market = {
                "top_bullish": nse_data.nlargest(10, "p_change")[ ["symbol", "last_price", "p_change", "volume", "change"] ],
                "top_bearish": nse_data.nsmallest(10, "p_change")[ ["symbol", "last_price", "p_change", "volume", "change"] ],
                "top_volume": nse_data.nlargest(10, "volume")[ ["symbol", "last_price", "p_change", "volume", "change"] ],
                "oversold": nse_data[nse_data["p_change"] <= -2].nsmallest(10, "p_change")[["symbol", "last_price", "p_change", "volume", "change"]],
                "overbought": nse_data[nse_data["p_change"] >= 2].nlargest(10, "p_change")[["symbol", "last_price", "p_change", "volume", "change"]],
                "top_gainers": nse_data.nlargest(10, "p_change")[["symbol", "last_price", "p_change", "volume", "change"]],
                "top_losers": nse_data.nsmallest(10, "p_change")[["symbol", "last_price", "p_change", "volume", "change"]],
            }
            st.subheader("NSE top bullish")
            st.dataframe(nse_market["top_bullish"], use_container_width=True)
            st.subheader("NSE top bearish")
            st.dataframe(nse_market["top_bearish"], use_container_width=True)
            st.subheader("NSE top volume")
            st.dataframe(nse_market["top_volume"], use_container_width=True)
            st.subheader("NSE oversold")
            st.dataframe(nse_market["oversold"], use_container_width=True)
            st.subheader("NSE overbought")
            st.dataframe(nse_market["overbought"], use_container_width=True)

    st.subheader("Forecasts")
    st.json({"forecasts": forecasts or [], "metrics": metrics or {}})

    st.subheader("Recent candles")
    st.dataframe(data if data is not None else [])
    return state


def main():
    if st is None:
        print("Streamlit is not installed; the dashboard state builder remains available for tests and scripts.")
        return

    use_nse_live_data = os.getenv("USE_NSE_LIVE_DATA", "1").lower() in {"1", "true", "yes", "y"}
    if use_nse_live_data:
        nse_data, nse_meta = build_nse_market_dashboard()
        if not nse_data.empty:
            data = nse_data.copy()
            data = data.rename(columns={"symbol": "symbol", "last_price": "close", "volume": "volume", "p_change": "change_pct"})
            forecasts = [{"symbol": symbol, "predicted_class": "LIVE", "horizon_minutes": 5} for symbol in sorted(data["symbol"].unique())]
            metrics = {"accuracy": 0.0, "coverage": 1.0, "n_samples": int(len(data))}
            market_context = {"market_regime": "LIVE_NSE_MARKET", "provider": nse_meta.get("provider", "nse-market-screen"), "symbol_count": len(data["symbol"].unique()), "sample_window_minutes": 60}
            render_dashboard(data=data, forecasts=forecasts, metrics=metrics, market_context=market_context)
            return

    data, forecasts, metrics, market_context = build_default_dashboard_data()
    render_dashboard(data=data, forecasts=forecasts, metrics=metrics, market_context=market_context)


if __name__ == "__main__":
    main()
