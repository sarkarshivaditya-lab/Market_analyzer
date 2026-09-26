"""Multi-horizon return forecasting."""
from __future__ import annotations

import pandas as pd

from market_analyzer.models.forecasting import ReturnForecaster


class MultiHorizonForecaster:
    def __init__(self, horizons=(1, 5, 20), random_state: int = 42):
        self.horizons = tuple(horizons)
        self.random_state = random_state
        self.models: dict[int, ReturnForecaster] = {}

    def fit(self, frame: pd.DataFrame, feature_columns: list[str], train_end):
        self.models = {}
        for horizon in self.horizons:
            model = ReturnForecaster(horizon=horizon, random_state=self.random_state)
            model.fit(frame, feature_columns, train_end=train_end)
            self.models[horizon] = model
        return self

    def predict(self, frame: pd.DataFrame) -> pd.DataFrame:
        keys = frame[["date", "tic"]].drop_duplicates().copy()
        for horizon, model in self.models.items():
            pred = model.predict(frame)[["date", "tic", "expected_return"]].rename(
                columns={"expected_return": f"expected_return_{horizon}d"}
            )
            keys = keys.merge(pred, on=["date", "tic"], how="left")
        return keys

    def latest(self, frame: pd.DataFrame) -> pd.DataFrame:
        out = self.predict(frame)
        return out.sort_values("date").groupby("tic").tail(1).reset_index(drop=True)
