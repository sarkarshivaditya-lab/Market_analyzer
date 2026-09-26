from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

@dataclass
class RegimeSnapshot:
    symbol: str
    regime: int
    label: str
    probability: float

class MarketRegimeModel:
    def __init__(self, n_regimes: int = 4, random_state: int = 42):
        self.n_regimes = n_regimes
        self.model = GaussianMixture(n_components=n_regimes, covariance_type="full", n_init=5, random_state=random_state)
        self.scaler = StandardScaler()
        self.features: list[str] = []
        self.labels: dict[int, str] = {}

    def fit(self, frame: pd.DataFrame, feature_columns: list[str]) -> "MarketRegimeModel":
        self.features = [c for c in feature_columns if c in frame.columns]
        x = frame[self.features].replace([np.inf, -np.inf], np.nan).dropna()
        if len(x) < self.n_regimes * 20:
            raise ValueError("Not enough observations for regime training.")
        z = self.scaler.fit_transform(x)
        self.model.fit(z)
        states = self.model.predict(z)
        stats = pd.DataFrame({"state": states, "ret": frame.loc[x.index, "return_1d"].to_numpy()})
        means = stats.groupby("state")["ret"].mean().sort_values()
        ordered = list(means.index)
        names = ["bear", "defensive", "neutral", "bull", "strong_bull"]
        for rank, state in enumerate(ordered):
            self.labels[int(state)] = names[min(rank, len(names)-1)]
        return self

    def predict_latest(self, frame: pd.DataFrame) -> pd.DataFrame:
        x = frame[self.features].replace([np.inf, -np.inf], np.nan)
        valid = x.notna().all(axis=1)
        z = self.scaler.transform(x.loc[valid])
        p = self.model.predict_proba(z)
        state = p.argmax(axis=1)
        out = frame.loc[valid, ["date", "tic"]].copy()
        out["regime"] = state
        out["regime_label"] = [self.labels.get(int(s), "unknown") for s in state]
        out["regime_probability"] = p.max(axis=1)
        return out
