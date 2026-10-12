from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd

from features.technical import compute_rsi

MARKET_TIMEZONE = "Asia/Kolkata"
STALE_AFTER = timedelta(minutes=10)

DEFAULT_SECTORS = {
    "RELIANCE": "Energy",
    "TCS": "IT",
    "INFY": "IT",
    "HDFCBANK": "Bank",
    "ICICIBANK": "Bank",
    "SBIN": "Bank",
    "LTIM": "IT",
    "ITC": "FMCG",
    "KOTAKBANK": "Bank",
    "AXISBANK": "Bank",
    "BHARTIARTL": "Telecom",
    "LT": "Industrials",
    "MARUTI": "Auto",
    "M&M": "Auto",
    "SUNPHARMA": "Pharma",
    "TATAMOTORS": "Auto",
    "BAJFINANCE": "Financials",
    "HINDUNILVR": "FMCG",
    "ADANIENT": "Industrials",
    "TITAN": "Consumer",
}

WATCHLIST_COLUMNS = [
    "Symbol",
    "Sector",
    "Direction",
    "Score",
    "Eligibility",
    "Last",
    "Price < 500",
    "Avg traded value (Cr)",
    "Avg daily volume",
    "Spread %",
    "Relative volume",
    "ORB / Retest",
    "VWAP side",
    "RSI (14)",
    "Market alignment",
    "Sector alignment",
    "Reward / Risk",
    "VWAP confirmed",
    "ORB confirmed",
    "Relative volume confirmed",
    "First retest held",
    "Market/sector aligned",
    "Risk/reward confirmed",
    "Catalyst status",
    "Sentiment status",
    "Missing data",
    "Rule failures",
]


def _market_timestamps(values: pd.Series) -> pd.Series:
    timestamps: list[pd.Timestamp] = []
    for value in values:
        try:
            timestamp = pd.Timestamp(value)
        except (TypeError, ValueError):
            timestamps.append(pd.NaT)
            continue
        if pd.isna(timestamp):
            timestamps.append(pd.NaT)
        elif timestamp.tzinfo is None:
            timestamps.append(timestamp.tz_localize(MARKET_TIMEZONE))
        else:
            timestamps.append(timestamp.tz_convert(MARKET_TIMEZONE))
    return pd.Series(pd.DatetimeIndex(timestamps), index=values.index)


def _prepare_bars(data: pd.DataFrame | None) -> pd.DataFrame:
    required = {"symbol", "timestamp", "open", "high", "low", "close", "volume"}
    if data is None or data.empty or not required.issubset(data.columns):
        return pd.DataFrame()

    frame = data.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
    frame["timestamp"] = _market_timestamps(frame["timestamp"])
    for column in ("open", "high", "low", "close", "volume", "bid", "ask"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
    if frame.empty:
        return frame

    bars: list[pd.DataFrame] = []
    aggregations: dict[str, str] = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    for optional in ("bid", "ask"):
        if optional in frame.columns:
            aggregations[optional] = "last"

    for symbol, group in frame.groupby("symbol", sort=False):
        group = group.set_index("timestamp").sort_index()
        resampled = group.resample(
            "5min",
            origin="start_day",
            offset="15min",
            label="left",
            closed="left",
        ).agg(aggregations)
        resampled = resampled.dropna(subset=["close"])
        resampled["symbol"] = symbol
        bars.append(resampled.reset_index())

    if not bars:
        return pd.DataFrame()
    return pd.concat(bars, ignore_index=True).sort_values(["symbol", "timestamp"]).reset_index(drop=True)


def _daily_liquidity(daily_data: pd.DataFrame | None, symbol: str, current_date: Any) -> tuple[float | None, float | None]:
    required = {"symbol", "timestamp", "close", "volume"}
    if daily_data is None or daily_data.empty or not required.issubset(daily_data.columns):
        return None, None

    frame = daily_data.loc[daily_data["symbol"].astype(str).str.upper().eq(symbol)].copy()
    if frame.empty:
        return None, None
    frame["timestamp"] = _market_timestamps(frame["timestamp"])
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "close", "volume"])
    frame = frame.loc[frame["timestamp"].dt.date < current_date].sort_values("timestamp").tail(20)
    if len(frame) < 20:
        return None, None

    traded_value_column = "turnover" if "turnover" in frame.columns else None
    if traded_value_column:
        traded_value = pd.to_numeric(frame[traded_value_column], errors="coerce")
        average_value = traded_value.mean()
    else:
        average_value = (frame["close"] * frame["volume"]).mean()
    return float(average_value), float(frame["volume"].mean())


def _relative_volume(bars: pd.DataFrame, symbol: str, current_date: Any, current_time: pd.Timestamp) -> float | None:
    symbol_bars = bars.loc[bars["symbol"].eq(symbol)].copy()
    symbol_bars["session_date"] = symbol_bars["timestamp"].dt.date
    symbol_bars["slot"] = (
        (symbol_bars["timestamp"].dt.hour * 60 + symbol_bars["timestamp"].dt.minute) - 555
    ) // 5
    current = symbol_bars.loc[symbol_bars["session_date"].eq(current_date)].sort_values("timestamp")
    current_slot = int(((current_time.hour * 60 + current_time.minute) - 555) // 5)
    current_volume = float(current.loc[current["slot"].le(current_slot), "volume"].sum())
    previous_dates = sorted(date for date in symbol_bars["session_date"].unique() if date < current_date)[-5:]
    if len(previous_dates) < 5:
        return None

    historical: list[float] = []
    for session_date in previous_dates:
        session = symbol_bars.loc[symbol_bars["session_date"].eq(session_date)].sort_values("timestamp")
        same_time = session.loc[session["slot"].le(current_slot)]
        if not same_time.empty:
            historical.append(float(same_time["volume"].sum()))
    if len(historical) < 5 or sum(historical) <= 0:
        return None
    return current_volume / (sum(historical) / len(historical))


def _opening_range_setup(session: pd.DataFrame) -> dict[str, Any]:
    local_time = session["timestamp"].dt.time
    opening = session.loc[(local_time >= pd.Timestamp("09:15").time()) & (local_time < pd.Timestamp("09:30").time())]
    if len(opening) < 3:
        return {"status": "OPENING RANGE INCOMPLETE", "direction": None, "breakout_confirmed": False}

    range_high = float(opening["high"].max())
    range_low = float(opening["low"].min())
    range_size = range_high - range_low
    after_open = session.loc[session["timestamp"].dt.time >= pd.Timestamp("09:30").time()].sort_values("timestamp")
    breakout: tuple[str, pd.Series] | None = None
    for _, bar in after_open.iterrows():
        if float(bar["close"]) > range_high:
            breakout = ("UP", bar)
            break
        if float(bar["close"]) < range_low:
            breakout = ("DOWN", bar)
            break
    if breakout is None:
        return {"status": "NO BREAKOUT", "direction": None, "breakout_confirmed": False}

    direction, breakout_bar = breakout
    level = range_high if direction == "UP" else range_low
    subsequent = after_open.loc[after_open["timestamp"] > breakout_bar["timestamp"]]
    for _, retest in subsequent.iterrows():
        touched = float(retest["low"]) <= level if direction == "UP" else float(retest["high"]) >= level
        if not touched:
            continue
        held = float(retest["close"]) >= level if direction == "UP" else float(retest["close"]) <= level
        if not held:
            return {"status": f"{direction}: FIRST RETEST FAILED", "direction": direction, "breakout_confirmed": True}
        entry = float(retest["close"])
        stop = float(retest["low"]) if direction == "UP" else float(retest["high"])
        target = range_high + range_size if direction == "UP" else range_low - range_size
        risk = entry - stop if direction == "UP" else stop - entry
        reward = target - entry if direction == "UP" else entry - target
        reward_to_risk = reward / risk if risk > 0 else None
        return {
            "status": f"{direction}: FIRST RETEST HELD",
            "direction": direction,
            "breakout_confirmed": True,
            "reward_to_risk": reward_to_risk,
            "entry": entry,
            "stop": stop,
            "target": target,
        }
    return {"status": f"{direction}: AWAITING RETEST", "direction": direction, "breakout_confirmed": True}


def _reference_direction(
    reference_data: pd.DataFrame | None,
    session_date: Any,
    latest_timestamp: pd.Timestamp,
    stale_after: timedelta,
) -> int | None:
    reference = _prepare_bars(reference_data)
    if reference.empty:
        return None
    reference["session_date"] = reference["timestamp"].dt.date
    reference = reference.loc[
        reference["session_date"].eq(session_date) & reference["timestamp"].le(latest_timestamp)
    ].sort_values("timestamp")
    if len(reference) < 2:
        return None
    reference_age = latest_timestamp - reference["timestamp"].iloc[-1]
    if not timedelta(0) <= reference_age <= stale_after:
        return None
    first_close = float(reference["close"].iloc[0])
    last_close = float(reference["close"].iloc[-1])
    return 1 if last_close > first_close else -1 if last_close < first_close else 0


def build_orb_watchlist(
    intraday_data: pd.DataFrame | None,
    *,
    daily_data: pd.DataFrame | None = None,
    market_data: pd.DataFrame | None = None,
    sector_data: dict[str, pd.DataFrame] | None = None,
    sector_by_symbol: dict[str, str] | None = None,
    top_n: int = 20,
    now: pd.Timestamp | None = None,
    stale_after: timedelta = STALE_AFTER,
) -> pd.DataFrame:
    """Rank intraday candidates against the proposed ORB research rubric (0-100)."""
    bars = _prepare_bars(intraday_data)
    if bars.empty:
        return pd.DataFrame(columns=WATCHLIST_COLUMNS)

    current_time = pd.Timestamp.now(tz=MARKET_TIMEZONE) if now is None else pd.Timestamp(now)
    current_time = current_time.tz_localize(MARKET_TIMEZONE) if current_time.tzinfo is None else current_time.tz_convert(MARKET_TIMEZONE)
    bars = bars.loc[bars["timestamp"] + pd.Timedelta(minutes=5) <= current_time].copy()
    if bars.empty:
        return pd.DataFrame(columns=WATCHLIST_COLUMNS)
    sector_map = {**DEFAULT_SECTORS, **{key.upper(): value for key, value in (sector_by_symbol or {}).items()}}
    sector_frames = sector_data or {}
    rows: list[dict[str, Any]] = []

    for symbol, symbol_bars in bars.groupby("symbol", sort=False):
        symbol_bars = symbol_bars.sort_values("timestamp").copy()
        latest = symbol_bars.iloc[-1]
        latest_timestamp = latest["timestamp"]
        session_date = latest_timestamp.date()
        session = symbol_bars.loc[symbol_bars["timestamp"].dt.date.eq(session_date)].copy()
        if session.empty:
            continue

        missing: list[str] = []
        score = 0.0
        direction_data = _opening_range_setup(session)
        direction = direction_data.get("direction")
        rr = direction_data.get("reward_to_risk")
        orb_status = direction_data["status"]

        average_value, average_volume = _daily_liquidity(daily_data, symbol, session_date)
        if average_value is None or average_volume is None:
            missing.append("20-session daily liquidity")
        else:
            score += 10.0 if average_value >= 50_000_000 else 0.0
            score += 5.0 if average_volume >= 200_000 else 0.0

        spread_pct: float | None = None
        if "bid" in symbol_bars.columns and "ask" in symbol_bars.columns:
            bid, ask = latest.get("bid"), latest.get("ask")
            midpoint = (float(bid) + float(ask)) / 2 if pd.notna(bid) and pd.notna(ask) else 0.0
            if midpoint > 0 and float(ask) >= float(bid):
                spread_pct = (float(ask) - float(bid)) / midpoint * 100
                score += 10.0 if spread_pct <= 0.10 else 0.0
        if spread_pct is None:
            missing.append("bid/ask spread")

        relative_volume = _relative_volume(bars, symbol, session_date, latest_timestamp)
        if relative_volume is None:
            missing.append("same-time relative-volume baseline")
        else:
            score += min(20.0, max(0.0, relative_volume / 1.5 * 20.0))

        if direction is None:
            missing.append("completed ORB and first retest")
        else:
            score += 8.0
            if orb_status.endswith("FIRST RETEST HELD"):
                score += 12.0

        typical_price = (session["high"] + session["low"] + session["close"]) / 3
        cumulative_volume = session["volume"].cumsum().replace(0, pd.NA)
        vwap_values = (typical_price * session["volume"]).cumsum() / cumulative_volume
        vwap = float(vwap_values.iloc[-1]) if pd.notna(vwap_values.iloc[-1]) else None
        vwap_rising = len(vwap_values) >= 2 and pd.notna(vwap_values.iloc[-2]) and vwap_values.iloc[-1] > vwap_values.iloc[-2]
        vwap_falling = len(vwap_values) >= 2 and pd.notna(vwap_values.iloc[-2]) and vwap_values.iloc[-1] < vwap_values.iloc[-2]
        vwap_side = None
        if vwap is None:
            missing.append("VWAP")
        elif direction and ((direction == "UP" and float(latest["close"]) > vwap) or (direction == "DOWN" and float(latest["close"]) < vwap)):
            vwap_side = "SUPPORTIVE"
            score += 8.0
        else:
            vwap_side = "NOT SUPPORTIVE"

        rsi_values = compute_rsi(symbol_bars["close"].astype(float), window=14)
        rsi = float(rsi_values.iloc[-1]) if len(rsi_values) >= 15 else None
        if rsi is None:
            missing.append("RSI(14) history")
        elif direction and ((direction == "UP" and rsi > 50) or (direction == "DOWN" and rsi < 50)):
            score += 7.0

        market_direction = _reference_direction(market_data, session_date, latest_timestamp, stale_after)
        if market_direction is None:
            missing.append("fresh NIFTY alignment")
        elif direction and market_direction == (1 if direction == "UP" else -1):
            score += 5.0

        sector = sector_map.get(symbol)
        sector_direction = _reference_direction(sector_frames.get(sector), session_date, latest_timestamp, stale_after) if sector else None
        if sector_direction is None:
            missing.append("fresh sector alignment")
        elif direction and sector_direction == (1 if direction == "UP" else -1):
            score += 5.0

        if rr is None:
            missing.append("risk/reward from first retest")
        else:
            score += min(6.0, max(0.0, rr / 2.0 * 6.0))

        age = current_time - latest_timestamp
        fresh = timedelta(0) <= age <= stale_after
        if fresh:
            score += 2.0
        else:
            missing.append("fresh intraday data")

        rule_failures: list[str] = []
        if average_value is not None and average_value < 50_000_000:
            rule_failures.append("20-session traded value below 5 crore/day")
        if average_volume is not None and average_volume < 200_000:
            rule_failures.append("20-session volume below 2 lakh shares/day")
        if spread_pct is not None and spread_pct > 0.10:
            rule_failures.append("spread above 0.10%")
        if relative_volume is not None and relative_volume < 1.5:
            rule_failures.append("relative volume below 1.5x")
        if direction is None:
            rule_failures.append("no completed ORB breakout")
        elif not orb_status.endswith("FIRST RETEST HELD"):
            rule_failures.append("first retest has not held")
        if vwap is not None and vwap_side != "SUPPORTIVE":
            rule_failures.append("price is not on the supportive side of VWAP")
        if rsi is not None and direction and not (
            (direction == "UP" and rsi > 50) or (direction == "DOWN" and rsi < 50)
        ):
            rule_failures.append("RSI(14) does not confirm direction")
        if market_direction is not None and direction and market_direction != (1 if direction == "UP" else -1):
            rule_failures.append("NIFTY is not aligned")
        if sector_direction is not None and direction and sector_direction != (1 if direction == "UP" else -1):
            rule_failures.append("sector is not aligned")
        if rr is not None and rr < 2.0:
            rule_failures.append("reward/risk below 1:2")
        if not fresh:
            rule_failures.append("intraday data is stale or candle is incomplete")
        price_eligible = float(latest["close"]) < 500
        if not price_eligible:
            rule_failures.append("share price is not below 500")

        catalyst_verified = False
        catalyst_status = "UNVERIFIED (no news feed connected)"
        missing.append("verified catalyst and contradictory-news check")
        if catalyst_verified:
            score += 2.0

        vwap_confirmed = bool(
            direction == "UP" and vwap is not None and float(latest["close"]) > vwap and vwap_rising
            or direction == "DOWN" and vwap is not None and float(latest["close"]) < vwap and vwap_falling
        )
        orb_confirmed = bool(direction_data.get("breakout_confirmed") and direction in {"UP", "DOWN"})
        relative_volume_confirmed = relative_volume is not None and relative_volume >= 1.5
        retest_held = orb_status.endswith("FIRST RETEST HELD")
        market_sector_aligned = bool(
            direction
            and market_direction == (1 if direction == "UP" else -1)
            and sector_direction == (1 if direction == "UP" else -1)
        )
        risk_reward_confirmed = rr is not None and rr >= 2.0

        threshold_ok = (
            average_value is not None and average_value >= 50_000_000
            and average_volume is not None and average_volume >= 200_000
            and spread_pct is not None and spread_pct <= 0.10
            and relative_volume is not None and relative_volume >= 1.5
            and orb_status.endswith("FIRST RETEST HELD")
            and vwap_side == "SUPPORTIVE"
            and rsi is not None and direction is not None
            and ((direction == "UP" and rsi > 50) or (direction == "DOWN" and rsi < 50))
            and market_direction == (1 if direction == "UP" else -1)
            and sector_direction == (1 if direction == "UP" else -1)
            and rr is not None and rr >= 2.0
            and fresh
            and price_eligible
            and catalyst_verified
        )
        rows.append(
            {
                "Symbol": symbol,
                "Sector": sector or "Unknown",
                "Direction": direction or "UNCONFIRMED",
                "Score": round(min(score, 100.0), 2),
                "Eligibility": "ELIGIBLE" if threshold_ok else "INCOMPLETE" if missing else "FILTERS NOT MET",
                "Last": float(latest["close"]),
                "Price < 500": price_eligible,
                "Avg traded value (Cr)": round(average_value / 10_000_000, 2) if average_value is not None else None,
                "Avg daily volume": round(average_volume, 0) if average_volume is not None else None,
                "Spread %": round(spread_pct, 4) if spread_pct is not None else None,
                "Relative volume": round(relative_volume, 2) if relative_volume is not None else None,
                "ORB / Retest": orb_status,
                "VWAP side": vwap_side or "MISSING",
                "RSI (14)": round(rsi, 2) if rsi is not None else None,
                "Market alignment": "ALIGNED" if market_direction == (1 if direction == "UP" else -1) and direction else "MISSING / AGAINST",
                "Sector alignment": "ALIGNED" if sector_direction == (1 if direction == "UP" else -1) and direction else "MISSING / AGAINST",
                "Reward / Risk": round(rr, 2) if rr is not None else None,
                "VWAP confirmed": vwap_confirmed,
                "ORB confirmed": orb_confirmed,
                "Relative volume confirmed": relative_volume_confirmed,
                "First retest held": retest_held,
                "Market/sector aligned": market_sector_aligned,
                "Risk/reward confirmed": risk_reward_confirmed,
                "Catalyst status": catalyst_status,
                "Sentiment status": "PRICE / SECTOR ALIGNED; NEWS UNVERIFIED" if market_sector_aligned else "MIXED OR UNVERIFIED",
                "Missing data": ", ".join(missing) if missing else "None",
                "Rule failures": ", ".join(rule_failures) if rule_failures else "None",
            }
        )

    if not rows:
        return pd.DataFrame(columns=WATCHLIST_COLUMNS)
    result = pd.DataFrame(rows, columns=WATCHLIST_COLUMNS)
    eligibility_order = {"ELIGIBLE": 0, "FILTERS NOT MET": 1, "INCOMPLETE": 2}
    result["_eligibility_order"] = result["Eligibility"].map(eligibility_order)
    return (
        result.sort_values(["_eligibility_order", "Score"], ascending=[True, False], kind="stable")
        .drop(columns="_eligibility_order")
        .head(max(1, min(top_n, 20)))
        .reset_index(drop=True)
    )


__all__ = ["build_orb_watchlist"]