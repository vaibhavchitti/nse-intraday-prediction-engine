from __future__ import annotations

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - fallback for non-UI environments
    st = None

from dashboard.app import build_dashboard_state


def render_dashboard(data=None, forecasts=None, metrics=None):
    if st is None:
        return build_dashboard_state(data, forecasts=forecasts, metrics=metrics)

    state = build_dashboard_state(data, forecasts=forecasts, metrics=metrics)
    st.title("NSE Intraday Prediction Engine")
    st.caption("Research-only dashboard for historical and synthetic evaluation.")

    if state["status"] == "NO_DATA":
        st.warning("No market data is available yet. Upload or replay historical data to populate the dashboard.")
        return state

    st.metric("Status", state["status"])
    st.metric("Last scan", state["last_scan"] or "N/A")
    if metrics:
        st.metric("Accuracy", metrics.get("accuracy", 0.0))
    st.dataframe(data if data is not None else [])
    st.json({"forecasts": forecasts or [], "metrics": metrics or {}})
    return state


def main():
    if st is None:
        print("Streamlit is not installed; the dashboard state builder remains available for tests and scripts.")
        return
    render_dashboard()


if __name__ == "__main__":
    main()
