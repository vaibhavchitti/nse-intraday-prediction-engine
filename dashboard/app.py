from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd

from config import get_settings
from data.providers.base import ProviderError
from data.providers.nse_market_screen import NSEMarketScreenProvider
from data.providers.synthetic_provider import SyntheticDataProvider
from data.providers.yfinance_provider import YahooFinanceProvider
from features.technical import compute_rsi
from dashboard.chart_screener import build_daily_chart_scorecard
from dashboard.orb_screener import DEFAULT_SECTORS, build_orb_watchlist


def build_default_dashboard_data(
    symbols: list[str] | None = None,
    *,
    seed: int = 42,
    use_yahoo_data: bool | None = None,
) -> tuple[pd.DataFrame, list[dict], dict]:
    """Build the default dashboard payload using the configured market universe and YFinance by default."""
    selected_symbols = symbols or get_settings().universe or ["RELIANCE", "TCS", "INFY"]

    if use_yahoo_data is None:
        use_yahoo_data = True
    if not isinstance(use_yahoo_data, bool):
        use_yahoo_data = str(use_yahoo_data).lower() in {"1", "true", "yes", "y"}

    frames: list[pd.DataFrame] = []
    provider_name = "synthetic"

    if use_yahoo_data:
        try:
            provider = YahooFinanceProvider()
            end_dt = datetime.now(UTC)
            start_dt = end_dt - timedelta(days=7)
            for symbol in selected_symbols:
                candles = provider.fetch_candles(
                    symbol,
                    interval="1m",
                    start=start_dt.strftime("%Y-%m-%d"),
                    end=end_dt.strftime("%Y-%m-%d"),
                )
                if candles:
                    frames.append(pd.DataFrame(candles))
            if frames:
                provider_name = "yahoo-finance"
        except ProviderError:
            frames = []

    if not frames:
        provider = SyntheticDataProvider(seed=seed)
        for symbol in selected_symbols:
            candles = provider.fetch_candles(
                symbol,
                interval="1min",
                start="2024-01-01T09:15:00+05:30",
                end="2024-01-01T09:45:00+05:30",
            )
            if candles:
                frames.append(pd.DataFrame(candles))

    if frames:
        data = pd.concat(frames, ignore_index=True)
    else:
        data = pd.DataFrame()

    loaded_symbols = list(dict.fromkeys(data["symbol"].astype(str).str.upper())) if "symbol" in data.columns else []
    if not loaded_symbols:
        loaded_symbols = selected_symbols

    forecasts = [
        {"symbol": symbol, "predicted_class": "UP", "horizon_minutes": 5}
        for symbol in loaded_symbols
    ]
    metrics = {
        "accuracy": 0.68,
        "coverage": 0.9,
        "n_samples": int(len(data)),
    }
    market_context = {
        "market_regime": "SIMULATED_RANGE" if provider_name == "synthetic" else "LIVE_FREE_DATA",
        "symbol_count": len(loaded_symbols),
        "sample_window_minutes": 30,
        "provider": provider_name,
    }
    return data, forecasts, metrics, market_context


def build_dashboard_pipeline_state(
    data: pd.DataFrame | None,
    *,
    scan_result: dict | None = None,
    report: dict | None = None,
    forecasts: list[dict] | None = None,
    metrics: dict | None = None,
    market_context: dict | None = None,
) -> dict[str, Any]:
    """Combine the raw dashboard state with scan and research evidence into one displayable state."""
    state = build_dashboard_state(data, forecasts=forecasts, metrics=metrics, market_context=market_context)
    if state["status"] == "NO_DATA":
        return state

    state["scan"] = scan_result or {}
    state["report"] = report or {}
    return state


def build_empty_dashboard_state() -> dict[str, Any]:
    return {
        "status": "NO_DATA",
        "market_regime": "UNKNOWN",
        "last_scan": None,
        "forecasts": [],
        "metrics": {},
        "market_context": {},
    }


def build_watchlist_table(
    data: pd.DataFrame | None,
    *,
    selected_symbols: list[str] | None = None,
) -> pd.DataFrame:
    """Return a symbol-level table for watchlist rendering and filtering."""
    if data is None or data.empty:
        return pd.DataFrame(columns=["Symbol", "Last", "Change %", "Volume", "Last timestamp"])

    frame = data.copy()
    if "symbol" in frame.columns:
        frame["symbol"] = frame["symbol"].astype(str).str.upper()
    if selected_symbols:
        selected = {str(symbol).upper() for symbol in selected_symbols}
        frame = frame[frame["symbol"].isin(selected)] if "symbol" in frame.columns else frame.iloc[0:0]

    if frame.empty:
        return pd.DataFrame(columns=["Symbol", "Last", "Change %", "Volume", "Last timestamp"])

    rows: list[dict[str, Any]] = []
    for symbol, group in frame.groupby("symbol", sort=False):
        ordered = group.sort_values("timestamp") if "timestamp" in group.columns else group
        last_row = ordered.iloc[-1]
        prev_row = ordered.iloc[-2] if len(ordered) > 1 else last_row
        prev_close = float(prev_row.get("close", 0.0)) if "close" in prev_row.index else 0.0
        last_close = float(last_row.get("close", 0.0)) if "close" in last_row.index else 0.0
        change_pct = ((last_close - prev_close) / prev_close) if prev_close else 0.0
        rows.append(
            {
                "Symbol": str(symbol),
                "Last": last_close,
                "Change %": change_pct,
                "Volume": float(last_row.get("volume", 0.0)) if "volume" in last_row.index else 0.0,
                "Last timestamp": last_row.get("timestamp"),
            }
        )

    return pd.DataFrame(rows).sort_values("Change %", ascending=False).reset_index(drop=True)


def _empty_market_table() -> pd.DataFrame:
    return pd.DataFrame(columns=["Symbol", "Last", "Change %", "Volume", "RSI (14)", "EMA 9", "EMA 20", "VWAP", "Close / VWAP"])


def build_nse_market_dashboard() -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build the exchange-wide live NSE market screen and metadata used in the full dashboard."""
    try:
        provider = NSEMarketScreenProvider()
        rows = provider.fetch_market_screen()
    except Exception:
        return pd.DataFrame(), {"provider": "nse-market-screen", "status": "unavailable"}

    if not rows:
        return pd.DataFrame(), {"provider": "nse-market-screen", "status": "empty"}

    frame = pd.DataFrame(rows)
    frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce").fillna(0.0)
    frame["p_change"] = pd.to_numeric(frame["p_change"], errors="coerce").fillna(0.0)
    frame["last_price"] = pd.to_numeric(frame["last_price"], errors="coerce").fillna(0.0)
    frame["change"] = pd.to_numeric(frame["change"], errors="coerce").fillna(0.0)
    frame["turnover"] = pd.to_numeric(frame["turnover"], errors="coerce").fillna(0.0)

    market = {
        "provider": "nse-market-screen",
        "status": "live",
        "sample_count": len(frame),
        "timestamp": frame["timestamp"].iloc[0] if "timestamp" in frame.columns and not frame.empty else None,
    }
    return frame, market


def build_orb_research_watchlist() -> pd.DataFrame:
    """Fetch Yahoo research inputs and rank the configured core universe for the 5-minute ORB setup."""
    symbols = get_settings().universe
    provider = YahooFinanceProvider()
    index_provider = YahooFinanceProvider(symbol_suffix="")
    now_utc = datetime.now(UTC)
    start = (now_utc - timedelta(days=60)).strftime("%Y-%m-%d")
    daily_start = (now_utc - timedelta(days=400)).strftime("%Y-%m-%d")
    end = (now_utc + timedelta(days=1)).strftime("%Y-%m-%d")

    intraday_frames: list[pd.DataFrame] = []
    daily_frames: list[pd.DataFrame] = []
    for symbol in symbols:
        candles = provider.fetch_candles(symbol, interval="5m", start=start, end=end)
        daily = provider.fetch_candles(symbol, interval="1d", start=daily_start, end=end)
        if candles:
            bid, ask = provider.fetch_bid_ask(symbol)
            frame = pd.DataFrame(candles)
            frame["bid"] = bid
            frame["ask"] = ask
            intraday_frames.append(frame)
        if daily:
            daily_frames.append(pd.DataFrame(daily))

    if not intraday_frames:
        return build_orb_watchlist(pd.DataFrame())

    sector_index_symbols = {
        "Bank": "^NSEBANK",
        "IT": "^CNXIT",
        "Auto": "^CNXAUTO",
        "FMCG": "^CNXFMCG",
        "Energy": "^CNXENERGY",
        "Pharma": "^CNXPHARMA",
        "Financials": "^CNXFINANCE",
        "Industrials": "^CNXINFRA",
        "Consumer": "^CNXCONSUMPTION",
    }
    sector_data: dict[str, pd.DataFrame] = {}
    for sector in {DEFAULT_SECTORS.get(symbol) for symbol in symbols} - {None}:
        index_symbol = sector_index_symbols.get(sector)
        if not index_symbol:
            continue
        candles = index_provider.fetch_candles(index_symbol, interval="5m", start=start, end=end)
        if candles:
            sector_data[sector] = pd.DataFrame(candles)

    market_candles = index_provider.fetch_candles("^NSEI", interval="5m", start=start, end=end)
    return build_orb_watchlist(
        pd.concat(intraday_frames, ignore_index=True),
        daily_data=pd.concat(daily_frames, ignore_index=True) if daily_frames else None,
        market_data=pd.DataFrame(market_candles) if market_candles else None,
        sector_data=sector_data,
        now=pd.Timestamp.now(tz="Asia/Kolkata"),
    )


def build_daily_chart_research_scorecard() -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Fetch one-year daily history and return chart scores with every rule's result."""
    provider = YahooFinanceProvider()
    index_provider = YahooFinanceProvider(symbol_suffix="")
    now_utc = datetime.now(UTC)
    start = (now_utc - timedelta(days=400)).strftime("%Y-%m-%d")
    end = (now_utc + timedelta(days=1)).strftime("%Y-%m-%d")
    frames: list[pd.DataFrame] = []
    for symbol in get_settings().universe:
        candles = provider.fetch_candles(symbol, interval="1d", start=start, end=end)
        if candles:
            frames.append(pd.DataFrame(candles))
    if not frames:
        return build_daily_chart_scorecard(pd.DataFrame())
    nifty_candles = index_provider.fetch_candles("^NSEI", interval="1d", start=start, end=end)
    return build_daily_chart_scorecard(
        pd.concat(frames, ignore_index=True),
        pd.DataFrame(nifty_candles) if nifty_candles else None,
    )


def build_market_dashboard(data: pd.DataFrame | None) -> dict[str, pd.DataFrame]:
    """Build the live market-screen rankings used by the complete dashboard."""
    empty = {name: _empty_market_table() for name in [
        "top_bullish",
        "top_bearish",
        "top_volume",
        "oversold",
        "overbought",
        "top_gainers",
        "top_losers",
        "top_vwap",
        "top_ema",
    ]}
    if data is None or data.empty:
        return empty

    frame = data.copy()
    if "symbol" in frame.columns:
        frame["symbol"] = frame["symbol"].astype(str).str.upper()
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    if "close" not in frame.columns or "symbol" not in frame.columns:
        return empty

    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["volume"] = pd.to_numeric(frame.get("volume", 0), errors="coerce").fillna(0.0)

    rows: list[dict[str, Any]] = []
    for symbol, group in frame.groupby("symbol", sort=False):
        ordered = group.sort_values("timestamp").dropna(subset=["close"]).copy()
        if ordered.empty:
            continue

        ordered["volume"] = pd.to_numeric(ordered["volume"], errors="coerce").fillna(0.0)
        ordered["vwap"] = (ordered["close"] * ordered["volume"]).cumsum() / ordered["volume"].cumsum().replace(0, pd.NA)
        ordered["ema_9"] = ordered["close"].ewm(span=9, adjust=False).mean()
        ordered["ema_20"] = ordered["close"].ewm(span=20, adjust=False).mean()
        ordered["ema_50"] = ordered["close"].ewm(span=50, adjust=False).mean()
        ordered["rsi_14"] = compute_rsi(ordered["close"], window=14)
        ordered["change_pct"] = ordered["close"].pct_change().fillna(0.0)
        ordered["close_to_vwap"] = ((ordered["close"] - ordered["vwap"]) / ordered["vwap"]).replace([float("inf"), float("-inf")], pd.NA)

        last = ordered.iloc[-1]
        prev_close = ordered["close"].iloc[-2] if len(ordered) > 1 else last["close"]
        last_change = ((float(last["close"]) - float(prev_close)) / float(prev_close)) if prev_close else 0.0

        bullish_score = 0.0
        bullish_score += 3.0 if float(last["close"]) > float(last["ema_9"]) else 0.0
        bullish_score += 2.0 if float(last["ema_9"]) > float(last["ema_20"]) else 0.0
        bullish_score += 1.5 if float(last["ema_20"]) > float(last["ema_50"]) else 0.0
        bullish_score += 2.0 if float(last["rsi_14"]) > 55 else 0.0
        bullish_score += max(float(last_change), 0.0) * 100

        bearish_score = 0.0
        bearish_score += 3.0 if float(last["close"]) < float(last["ema_9"]) else 0.0
        bearish_score += 2.0 if float(last["ema_9"]) < float(last["ema_20"]) else 0.0
        bearish_score += 1.5 if float(last["ema_20"]) < float(last["ema_50"]) else 0.0
        bearish_score += 2.0 if float(last["rsi_14"]) < 45 else 0.0
        bearish_score += max(-float(last_change), 0.0) * 100

        rows.append(
            {
                "Symbol": str(symbol),
                "Last": float(last["close"]),
                "Change %": float(last_change),
                "Volume": float(last["volume"]),
                "RSI (14)": float(last["rsi_14"]),
                "EMA 9": float(last["ema_9"]),
                "EMA 20": float(last["ema_20"]),
                "VWAP": float(last["vwap"]),
                "Close / VWAP": float(last["close"]) / float(last["vwap"]) if float(last["vwap"]) else 0.0,
                "Bullish score": float(bullish_score),
                "Bearish score": float(bearish_score),
                "EMA trend": float(last["ema_9"]) / float(last["ema_20"]) if float(last["ema_20"]) else 0.0,
            }
        )

    if not rows:
        return empty

    summary = pd.DataFrame(rows)
    top_bullish = summary.sort_values(["Bullish score", "Change %", "RSI (14)"], ascending=[False, False, False]).head(10).reset_index(drop=True)
    top_bearish = summary.sort_values(["Bearish score", "Change %", "RSI (14)"], ascending=[False, False, True]).head(10).reset_index(drop=True)
    top_volume = summary.sort_values("Volume", ascending=False).head(10).reset_index(drop=True)
    oversold = summary[summary["RSI (14)"] <= 30].sort_values("RSI (14)", ascending=True).head(10).reset_index(drop=True)
    overbought = summary[summary["RSI (14)"] >= 70].sort_values("RSI (14)", ascending=False).head(10).reset_index(drop=True)
    top_gainers = summary.sort_values("Change %", ascending=False).head(10).reset_index(drop=True)
    top_losers = summary.sort_values("Change %", ascending=True).head(10).reset_index(drop=True)
    top_vwap = summary.sort_values("Close / VWAP", ascending=False).head(10).reset_index(drop=True)
    top_ema = summary.sort_values("EMA trend", ascending=False).head(10).reset_index(drop=True)

    return {
        "top_bullish": top_bullish[["Symbol", "Last", "Change %", "Volume", "RSI (14)", "EMA 9", "EMA 20", "VWAP", "Close / VWAP"]],
        "top_bearish": top_bearish[["Symbol", "Last", "Change %", "Volume", "RSI (14)", "EMA 9", "EMA 20", "VWAP", "Close / VWAP"]],
        "top_volume": top_volume[["Symbol", "Last", "Change %", "Volume", "RSI (14)", "EMA 9", "EMA 20", "VWAP", "Close / VWAP"]],
        "oversold": oversold[["Symbol", "Last", "Change %", "Volume", "RSI (14)", "EMA 9", "EMA 20", "VWAP", "Close / VWAP"]],
        "overbought": overbought[["Symbol", "Last", "Change %", "Volume", "RSI (14)", "EMA 9", "EMA 20", "VWAP", "Close / VWAP"]],
        "top_gainers": top_gainers[["Symbol", "Last", "Change %", "Volume", "RSI (14)", "EMA 9", "EMA 20", "VWAP", "Close / VWAP"]],
        "top_losers": top_losers[["Symbol", "Last", "Change %", "Volume", "RSI (14)", "EMA 9", "EMA 20", "VWAP", "Close / VWAP"]],
        "top_vwap": top_vwap[["Symbol", "Last", "Change %", "Volume", "RSI (14)", "EMA 9", "EMA 20", "VWAP", "Close / VWAP"]],
        "top_ema": top_ema[["Symbol", "Last", "Change %", "Volume", "RSI (14)", "EMA 9", "EMA 20", "VWAP", "Close / VWAP"]],
    }


def build_dashboard_state(
    data: pd.DataFrame | None,
    forecasts: list[dict] | None = None,
    metrics: dict | None = None,
    market_context: dict | None = None,
) -> dict[str, Any]:
    if data is None or data.empty:
        return build_empty_dashboard_state()

    last_scan = None
    if "timestamp" in data.columns:
        last_scan_timestamp = pd.to_datetime(data["timestamp"], errors="coerce").max()
        if pd.notna(last_scan_timestamp):
            last_scan = pd.Timestamp(last_scan_timestamp).isoformat()

    state = {
        "status": "READY",
        "market_regime": (market_context or {}).get("market_regime", "UNKNOWN"),
        "last_scan": last_scan,
        "forecasts": forecasts or [],
        "metrics": metrics or {},
        "market_context": market_context or {},
    }
    return state
