from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    project_name: str = "nse_intraday_prediction_engine"
    data_dir: Path = Path("data")
    raw_data_dir: Path = Path("data/raw")
    market_timezone: str = "Asia/Kolkata"
    trading_start_hour: int = 9
    trading_start_minute: int = 15
    trading_end_hour: int = 15
    trading_end_minute: int = 30
    max_stale_minutes: int = 10
    lookback_minutes: int = 60
    synthetic_seed: int = 42
    fyers_api_key: Optional[str] = None
    fyers_api_secret: Optional[str] = None
    fyers_access_token: Optional[str] = None
    fyers_base_url: str = "https://api.fyers.in"
    universe: list[str] = field(
        default_factory=lambda: [
            "RELIANCE",
            "TCS",
            "INFY",
            "HDFCBANK",
            "ICICIBANK",
            "SBIN",
            "LTIM",
            "ITC",
            "KOTAKBANK",
            "AXISBANK",
        ]
    )


def build_settings() -> Settings:
    return Settings(
        project_name=os.getenv("PROJECT_NAME", "nse_intraday_prediction_engine"),
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        raw_data_dir=Path(os.getenv("RAW_DATA_DIR", "data/raw")),
        market_timezone=os.getenv("MARKET_TIMEZONE", "Asia/Kolkata"),
        trading_start_hour=int(os.getenv("TRADING_START_HOUR", "9")),
        trading_start_minute=int(os.getenv("TRADING_START_MINUTE", "15")),
        trading_end_hour=int(os.getenv("TRADING_END_HOUR", "15")),
        trading_end_minute=int(os.getenv("TRADING_END_MINUTE", "30")),
        max_stale_minutes=int(os.getenv("MAX_STALE_MINUTES", "10")),
        lookback_minutes=int(os.getenv("LOOKBACK_MINUTES", "60")),
        synthetic_seed=int(os.getenv("SYNTHETIC_SEED", "42")),
        fyers_api_key=os.getenv("FYERS_API_KEY"),
        fyers_api_secret=os.getenv("FYERS_API_SECRET"),
        fyers_access_token=os.getenv("FYERS_ACCESS_TOKEN"),
        fyers_base_url=os.getenv("FYERS_BASE_URL", "https://api.fyers.in"),
        universe=[item.strip() for item in os.getenv("UNIVERSE", "").split(",") if item.strip()],
    )


def validate_settings(settings: Settings) -> None:
    if settings.trading_start_hour < 0 or settings.trading_start_hour > 23:
        raise ValueError("TRADING_START_HOUR must be between 0 and 23")
    if settings.trading_end_hour < 0 or settings.trading_end_hour > 23:
        raise ValueError("TRADING_END_HOUR must be between 0 and 23")
    if settings.max_stale_minutes <= 0:
        raise ValueError("MAX_STALE_MINUTES must be > 0")
    if not settings.market_timezone:
        raise ValueError("MARKET_TIMEZONE must be set")


def get_settings() -> Settings:
    settings = build_settings()
    validate_settings(settings)
    return settings
