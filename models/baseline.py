from __future__ import annotations

from typing import Sequence

import pandas as pd


class AlwaysFlatBaseline:
    def fit(self, features, labels=None):
        return self

    def predict(self, returns: Sequence[float] | None = None):
        return "FLAT"


class PriceTrendBaseline:
    def fit(self, features, labels=None):
        return self

    def predict(self, returns: Sequence[float] | None = None):
        values = pd.Series(list(returns or [])).dropna()
        if values.empty:
            return "FLAT"

        rolling_mean = values.tail(5).mean()
        if rolling_mean > 0.002:
            return "UP"
        if rolling_mean < -0.002:
            return "DOWN"
        return "FLAT"


class MomentumBaseline:
    def fit(self, features, labels=None):
        return self

    def predict(self, returns: Sequence[float] | None = None):
        values = pd.Series(list(returns or [])).dropna()
        if values.empty:
            return "FLAT"

        recent = values.tail(3)
        if recent.iloc[-1] > 0:
            return "UP"
        if recent.iloc[-1] < 0:
            return "DOWN"
        return "FLAT"
