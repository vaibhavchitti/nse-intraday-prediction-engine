from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

RULES_PER_COMPONENT = {
    "Trend": 5,
    "Momentum": 5,
    "Volume": 4,
    "Volatility": 4,
    "Support / resistance": 4,
}
COMPONENT_WEIGHTS = {component: 20.0 for component in RULES_PER_COMPONENT}
RATING_BANDS = (
    (75, "strong bullish"),
    (60, "bullish"),
    (40, "neutral"),
    (25, "bearish"),
    (0, "strong bearish"),
)


def _prepare_daily(data: pd.DataFrame | None, symbol: str | None = None) -> pd.DataFrame:
    required = {"timestamp", "high", "low", "close", "volume"}
    if data is None or data.empty or not required.issubset(data.columns):
        return pd.DataFrame()
    frame = data.copy()
    if "symbol" in frame.columns:
        frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
        if symbol is not None:
            frame = frame.loc[frame["symbol"].eq(symbol.upper())].copy()
    elif symbol is not None:
        frame["symbol"] = symbol.upper()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    for column in ("open", "high", "low", "close", "volume"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "high", "low", "close", "volume"])
    return frame.sort_values("timestamp").drop_duplicates("timestamp", keep="last").tail(300).reset_index(drop=True)


def _rating(score: float) -> str:
    return next(label for threshold, label in RATING_BANDS if score >= threshold)


def _supertrend(frame: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    midpoint = (frame["high"] + frame["low"]) / 2
    basic_upper = midpoint + multiplier * atr
    basic_lower = midpoint - multiplier * atr
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    trend = pd.Series(1, index=frame.index, dtype="int64")
    output = pd.Series(np.nan, index=frame.index, dtype="float64")

    for index in range(1, len(frame)):
        if pd.isna(atr.iloc[index]):
            continue
        if pd.isna(final_upper.iloc[index - 1]) or pd.isna(final_lower.iloc[index - 1]):
            final_upper.iloc[index] = basic_upper.iloc[index]
            final_lower.iloc[index] = basic_lower.iloc[index]
            trend.iloc[index] = 1
            output.iloc[index] = final_lower.iloc[index]
            continue
        if basic_upper.iloc[index] < final_upper.iloc[index - 1] or frame["close"].iloc[index - 1] > final_upper.iloc[index - 1]:
            final_upper.iloc[index] = basic_upper.iloc[index]
        else:
            final_upper.iloc[index] = final_upper.iloc[index - 1]
        if basic_lower.iloc[index] > final_lower.iloc[index - 1] or frame["close"].iloc[index - 1] < final_lower.iloc[index - 1]:
            final_lower.iloc[index] = basic_lower.iloc[index]
        else:
            final_lower.iloc[index] = final_lower.iloc[index - 1]

        if trend.iloc[index - 1] < 0 and frame["close"].iloc[index] > final_upper.iloc[index]:
            trend.iloc[index] = 1
        elif trend.iloc[index - 1] > 0 and frame["close"].iloc[index] < final_lower.iloc[index]:
            trend.iloc[index] = -1
        else:
            trend.iloc[index] = trend.iloc[index - 1]
        output.iloc[index] = final_lower.iloc[index] if trend.iloc[index] > 0 else final_upper.iloc[index]
    return output


def _adx_and_direction(frame: pd.DataFrame, period: int = 14) -> tuple[float | None, float | None, float | None]:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    upward = frame["high"].diff()
    downward = -frame["low"].diff()
    plus_dm = upward.where((upward > downward) & (upward > 0), 0.0)
    minus_dm = downward.where((downward > upward) & (downward > 0), 0.0)
    smooth_tr = true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / smooth_tr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / smooth_tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    values = (adx.iloc[-1], plus_di.iloc[-1], minus_di.iloc[-1])
    return tuple(None if pd.isna(value) else float(value) for value in values)


def score_daily_chart(
    symbol: str,
    daily_history: pd.DataFrame,
    nifty_history: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Score 22 latest-close chart checks across five equally weighted 20-point components."""
    frame = _prepare_daily(daily_history, symbol)
    rules: list[dict[str, Any]] = []

    def add(component: str, rule: str, passed: bool, detail: str) -> None:
        rules.append({"component": component, "rule": rule, "passed": bool(passed), "detail": detail})

    if frame.empty:
        for component, count in RULES_PER_COMPONENT.items():
            for index in range(count):
                add(component, f"Rule {index + 1}", False, "Required daily OHLCV history unavailable")
        component_scores = {component: 0.0 for component in RULES_PER_COMPONENT}
        return {
            "symbol": symbol.upper(),
            "score": 0.0,
            "rating": _rating(0.0),
            "component_scores": component_scores,
            "rules": rules,
            "as_of": None,
            "data_status": "missing daily OHLCV history",
        }

    close, high, low, volume = frame["close"], frame["high"], frame["low"], frame["volume"]
    last_close = float(close.iloc[-1])
    previous_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1
    ).max(axis=1)
    atr14 = true_range.rolling(14, min_periods=14).mean()
    atr14_value = float(atr14.iloc[-1]) if pd.notna(atr14.iloc[-1]) else None
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    sma200 = close.rolling(200, min_periods=200).mean()
    supertrend = _supertrend(frame)
    adx, plus_di, minus_di = _adx_and_direction(frame)
    weekly_close = frame.set_index("timestamp")["close"].resample("W-FRI").last().dropna()
    weekly_ema10 = weekly_close.ewm(span=10, adjust=False).mean()

    trend_checks = [
        (
            "Close above EMA20 and 200-day SMA",
            len(frame) >= 200 and last_close > float(ema20.iloc[-1]) and pd.notna(sma200.iloc[-1]) and last_close > float(sma200.iloc[-1]),
            f"Close {last_close:.2f}; EMA20 {ema20.iloc[-1]:.2f}; SMA200 {sma200.iloc[-1]:.2f}" if len(frame) >= 200 else "Need 200 daily bars",
        ),
        (
            "EMA20 above EMA50 above EMA200",
            len(frame) >= 200 and ema20.iloc[-1] > ema50.iloc[-1] > ema200.iloc[-1],
            "EMA20/50/200 stack is bullish" if len(frame) >= 200 and ema20.iloc[-1] > ema50.iloc[-1] > ema200.iloc[-1] else "EMA20/50/200 stack is not bullish or history is short",
        ),
        (
            "Close above SuperTrend(10, 3)",
            pd.notna(supertrend.iloc[-1]) and last_close > float(supertrend.iloc[-1]),
            f"Close {last_close:.2f}; SuperTrend {supertrend.iloc[-1]:.2f}" if pd.notna(supertrend.iloc[-1]) else "Need SuperTrend warm-up history",
        ),
        (
            "ADX14 >= 20 with positive directional index dominant",
            adx is not None and plus_di is not None and minus_di is not None and adx >= 20 and plus_di > minus_di,
            f"ADX {adx:.1f}; +DI {plus_di:.1f}; -DI {minus_di:.1f}" if adx is not None else "Need ADX warm-up history",
        ),
        (
            "Weekly close above 10-week EMA and prior week",
            len(weekly_close) >= 11 and weekly_close.iloc[-1] > weekly_ema10.iloc[-1] and weekly_close.iloc[-1] > weekly_close.iloc[-2],
            "Weekly trend is rising" if len(weekly_close) >= 11 and weekly_close.iloc[-1] > weekly_ema10.iloc[-1] and weekly_close.iloc[-1] > weekly_close.iloc[-2] else "Weekly trend is not confirmed or history is short",
        ),
    ]
    for item in trend_checks:
        add("Trend", *item)

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    rsi_value = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    roc3m = float((last_close / close.iloc[-64] - 1) * 100) if len(close) >= 64 else None
    lowest14, highest14 = low.rolling(14, min_periods=14).min(), high.rolling(14, min_periods=14).max()
    stoch_k = 100 * (close - lowest14) / (highest14 - lowest14).replace(0, np.nan)
    stoch_d = stoch_k.rolling(3, min_periods=3).mean()
    nifty = _prepare_daily(nifty_history)
    relative_3m = None
    if len(frame) >= 64 and not nifty.empty:
        stock_return = last_close / float(close.iloc[-64]) - 1
        nifty_close = nifty["close"]
        if len(nifty_close) >= 64 and float(nifty_close.iloc[-64]) != 0:
            relative_3m = stock_return - (float(nifty_close.iloc[-1]) / float(nifty_close.iloc[-64]) - 1)

    momentum_checks = [
        ("RSI14 between 50 and 70", rsi_value is not None and 50 <= rsi_value <= 70, f"RSI14 {rsi_value:.1f}" if rsi_value is not None else "Need RSI warm-up history"),
        ("MACD above signal and zero", macd.iloc[-1] > macd_signal.iloc[-1] and macd.iloc[-1] > 0, f"MACD {macd.iloc[-1]:.3f}; signal {macd_signal.iloc[-1]:.3f}"),
        ("3-month rate of change positive", roc3m is not None and roc3m > 0, f"3-month ROC {roc3m:.1f}%" if roc3m is not None else "Need 64 daily bars"),
        ("Stochastic %K above %D and below 80", pd.notna(stoch_k.iloc[-1]) and pd.notna(stoch_d.iloc[-1]) and stoch_k.iloc[-1] > stoch_d.iloc[-1] and stoch_k.iloc[-1] < 80, f"%K {stoch_k.iloc[-1]:.1f}; %D {stoch_d.iloc[-1]:.1f}" if pd.notna(stoch_d.iloc[-1]) else "Need Stochastic warm-up history"),
        ("3-month performance exceeds Nifty 50", relative_3m is not None and relative_3m > 0, f"Relative performance {relative_3m * 100:.1f} pp" if relative_3m is not None else "Need aligned 3-month stock and Nifty history"),
    ]
    for item in momentum_checks:
        add("Momentum", *item)

    obv = (np.sign(delta.fillna(0)) * volume).cumsum()
    cmf_multiplier = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    cmf20 = (cmf_multiplier * volume).rolling(20, min_periods=20).sum() / volume.rolling(20, min_periods=20).sum()
    daily_direction = np.sign(delta)
    recent_direction = daily_direction.tail(20)
    recent_volume = volume.tail(20)
    up_volume = float(recent_volume.loc[recent_direction > 0].sum())
    down_volume = float(recent_volume.loc[recent_direction < 0].sum())
    typical = (high + low + close) / 3
    vwap20 = (typical * volume).rolling(20, min_periods=20).sum() / volume.rolling(20, min_periods=20).sum()
    volume_checks = [
        ("OBV above its 20-day average", len(obv) >= 20 and obv.iloc[-1] > obv.rolling(20, min_periods=20).mean().iloc[-1], "OBV is above its 20-day average" if len(obv) >= 20 and obv.iloc[-1] > obv.rolling(20, min_periods=20).mean().iloc[-1] else "OBV is not above its 20-day average"),
        ("Chaikin Money Flow(20) positive", pd.notna(cmf20.iloc[-1]) and cmf20.iloc[-1] > 0, f"CMF20 {cmf20.iloc[-1]:.3f}" if pd.notna(cmf20.iloc[-1]) else "Need 20 valid daily bars"),
        ("Up-day volume exceeds down-day volume (20 sessions)", up_volume > down_volume and (daily_direction.tail(20) > 0).sum() > 0, f"Up volume {up_volume:,.0f}; down volume {down_volume:,.0f}"),
        ("Close above 20-day VWAP", pd.notna(vwap20.iloc[-1]) and last_close > vwap20.iloc[-1], f"Close {last_close:.2f}; 20-day VWAP {vwap20.iloc[-1]:.2f}" if pd.notna(vwap20.iloc[-1]) else "Need 20 valid daily bars"),
    ]
    for item in volume_checks:
        add("Volume", *item)

    atr_pct = atr14_value / last_close * 100 if atr14_value is not None and last_close > 0 else None
    bb_mid = close.rolling(20, min_periods=20).mean()
    bb_std = close.rolling(20, min_periods=20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_percent = (close.iloc[-1] - bb_mid.iloc[-1]) / (bb_upper.iloc[-1] - bb_mid.iloc[-1]) if pd.notna(bb_upper.iloc[-1]) and bb_upper.iloc[-1] != bb_mid.iloc[-1] else None
    high52 = float(high.tail(252).max())
    drawdown52 = (last_close / high52 - 1) * 100 if high52 > 0 else None
    volatility_checks = [
        ("ATR14 is 1%-5% of price", atr_pct is not None and 1 <= atr_pct <= 5, f"ATR14 {atr_pct:.2f}% of price" if atr_pct is not None else "Need ATR14 history"),
        ("Close is between Bollinger midline and upper band", bb_percent is not None and 0.5 <= bb_percent <= 1.05, f"Bollinger %B {bb_percent:.2f}" if bb_percent is not None else "Need Bollinger warm-up history"),
        ("Drawdown from 52-week high is no worse than 15%", drawdown52 is not None and drawdown52 >= -15, f"52-week-high drawdown {drawdown52:.1f}%" if drawdown52 is not None else "Need 52-week history"),
        ("ATR is contracting (5-day below 20-day average)", len(true_range) >= 20 and true_range.tail(5).mean() < true_range.tail(20).mean(), "5-day range is below its 20-day average" if len(true_range) >= 20 and true_range.tail(5).mean() < true_range.tail(20).mean() else "Volatility is not contracting or history is short"),
    ]
    for item in volatility_checks:
        add("Volatility", *item)

    previous20_high = high.shift(1).rolling(20, min_periods=20).max()
    previous20_low = low.shift(1).rolling(20, min_periods=20).min()
    previous252_high = high.shift(1).rolling(252, min_periods=200).max()
    resistance = float(previous252_high.iloc[-1]) if pd.notna(previous252_high.iloc[-1]) else None
    support = float(previous20_low.iloc[-1]) if pd.notna(previous20_low.iloc[-1]) else None
    breakout20 = pd.notna(previous20_high.iloc[-1]) and last_close > previous20_high.iloc[-1]
    resistance_room = (resistance - last_close) if resistance is not None and resistance > last_close else None
    support_distance = (last_close - support) if support is not None and support < last_close else None
    support_checks = [
        ("At least 1.5 ATR of room to 52-week resistance or breakout", atr14_value is not None and (breakout20 or resistance_room is None or resistance_room >= 1.5 * atr14_value), f"20-day breakout {bool(breakout20)}; room to 52-week high {resistance_room:.2f}" if resistance_room is not None else f"20-day breakout {bool(breakout20)}; no overhead 52-week resistance"),
        ("20-day support is below price and within 2 ATR", support_distance is not None and atr14_value is not None and 0 < support_distance <= 2 * atr14_value, f"Distance to 20-day support {support_distance:.2f}" if support_distance is not None else "Need 20-day support history"),
        ("Close breaks above prior 20-day high", bool(breakout20), f"Close {last_close:.2f}; prior 20-day high {previous20_high.iloc[-1]:.2f}" if pd.notna(previous20_high.iloc[-1]) else "Need 20 prior sessions"),
        ("Close is within 10% of 52-week high", drawdown52 is not None and drawdown52 >= -10, f"52-week-high drawdown {drawdown52:.1f}%" if drawdown52 is not None else "Need 52-week history"),
    ]
    for item in support_checks:
        add("Support / resistance", *item)

    component_scores: dict[str, float] = {}
    for component, max_points in COMPONENT_WEIGHTS.items():
        component_rules = [rule for rule in rules if rule["component"] == component]
        component_scores[component] = round(max_points * sum(rule["passed"] for rule in component_rules) / len(component_rules), 2)
    score = round(sum(component_scores.values()), 2)
    return {
        "symbol": symbol.upper(),
        "score": score,
        "rating": _rating(score),
        "component_scores": component_scores,
        "rules": rules,
        "as_of": frame["timestamp"].iloc[-1].isoformat(),
        "data_status": "complete lookback" if len(frame) >= 252 else f"partial lookback ({len(frame)} daily bars; 252 preferred)",
    }


def build_daily_chart_scorecard(
    daily_data: pd.DataFrame | None,
    nifty_history: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Return latest-close scores and full per-rule details for all symbols in daily_data."""
    columns = ["Symbol", "Score", "Rating", "Trend", "Momentum", "Volume", "Volatility", "Support / resistance", "Data status", "As of"]
    if daily_data is None or daily_data.empty or "symbol" not in daily_data.columns:
        return pd.DataFrame(columns=columns), {}
    summaries: list[dict[str, Any]] = []
    details: dict[str, dict[str, Any]] = {}
    for symbol in sorted(daily_data["symbol"].dropna().astype(str).str.upper().unique()):
        result = score_daily_chart(symbol, daily_data, nifty_history)
        details[symbol] = result
        summaries.append(
            {
                "Symbol": symbol,
                "Score": result["score"],
                "Rating": result["rating"],
                "Trend": result["component_scores"]["Trend"],
                "Momentum": result["component_scores"]["Momentum"],
                "Volume": result["component_scores"]["Volume"],
                "Volatility": result["component_scores"]["Volatility"],
                "Support / resistance": result["component_scores"]["Support / resistance"],
                "Data status": result["data_status"],
                "As of": result["as_of"],
            }
        )
    summary = pd.DataFrame(summaries, columns=columns).sort_values("Score", ascending=False).reset_index(drop=True)
    return summary, details


__all__ = ["build_daily_chart_scorecard", "score_daily_chart"]
