from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error


@dataclass
class ForecastResult:
    symbol: str
    horizon: int
    expected_return: float
    predicted_price: float
    validation_mae: float | None


class ReturnForecaster:
    def __init__(self, horizon: int = 5, max_iter: int = 250, random_state: int = 42):
        self.horizon = horizon
        self.model = HistGradientBoostingRegressor(
            max_iter=max_iter,
            learning_rate=0.05,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            random_state=random_state,
        )
        self.features: list[str] = []
        self.validation_mae: float | None = None

    def make_target(self, frame: pd.DataFrame) -> pd.Series:
        data = frame.sort_values(["tic", "date"]).copy()
        target = data.groupby("tic", group_keys=False)["close"].transform(
            lambda s: s.shift(-self.horizon) / s - 1.0
        )
        return target.reindex(frame.index)

    def fit(
        self,
        frame: pd.DataFrame,
        feature_columns: list[str],
        train_end: pd.Timestamp | None = None,
    ) -> "ReturnForecaster":
        data = frame.copy()
        self.features = [c for c in feature_columns if c in data.columns]
        if not self.features:
            raise ValueError("No usable forecasting features were supplied.")
        target = self.make_target(data)
        mask = data[self.features].notna().all(axis=1) & target.notna()
        if train_end is not None:
            dates = pd.to_datetime(data["date"])
            future_dates = (
                data.assign(_date=dates)
                .sort_values(["tic", "_date"])
                .groupby("tic")["_date"]
                .shift(-self.horizon)
                .reindex(data.index)
            )
            mask &= dates <= train_end
            mask &= future_dates <= pd.Timestamp(train_end)
        X = data.loc[mask, self.features].replace([np.inf, -np.inf], np.nan).dropna()
        y = target.loc[X.index]
        if len(X) < 100:
            raise ValueError("Not enough observations to train the forecaster.")
        self.model.fit(X, y)
        return self

    def predict_latest(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.copy()
        X = data[self.features].replace([np.inf, -np.inf], np.nan)
        valid = X.notna().all(axis=1)
        out = data.loc[valid, ["date", "tic", "close"]].copy()
        out["expected_return"] = self.model.predict(X.loc[valid])
        out["predicted_price"] = out["close"] * (1.0 + out["expected_return"])
        out["horizon"] = self.horizon
        return out.sort_values(["date", "tic"])

    predict = predict_latest

    def evaluate(self, frame: pd.DataFrame, end: pd.Timestamp) -> float:
        target = self.make_target(frame)
        data = frame.copy()
        X = data[self.features].replace([np.inf, -np.inf], np.nan)
        mask = (pd.to_datetime(data["date"]) > end) & X.notna().all(axis=1) & target.notna()
        if not mask.any():
            return float("nan")
        pred = self.model.predict(X.loc[mask])
        self.validation_mae = float(mean_absolute_error(target.loc[mask], pred))
        return self.validation_mae
