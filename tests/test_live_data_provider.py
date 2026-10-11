from __future__ import annotations

import pytest

from data.providers.fyers import FYERSDataProvider


def test_fyers_provider_requires_credentials():
    provider = FYERSDataProvider(api_key=None, api_secret=None, access_token=None)
    with pytest.raises(ValueError):
        provider.fetch_candles("RELIANCE")

    provider = FYERSDataProvider(api_key="demo", api_secret="demo", access_token="demo")
    assert provider._build_base_headers()["api-key"] == "demo"
    assert provider._build_base_headers()["access-token"] == "demo"
