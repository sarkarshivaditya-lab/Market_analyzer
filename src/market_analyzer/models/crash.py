from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score, roc_auc_score

@dataclass
class CrashMetrics:
    horizon: int
    threshold: float
    auc: float | None
    precision: float | None
    recall: float | None

class CrashRiskModel:
    def __init__(self, horizon: int = 20, drawdown_threshold: float = -0.10, random_state: int = 42):
        self.horizon = horizon
        self.drawdown_threshold = drawdown_threshold
        self.model = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0, random_state=random_state)
        self.features: list[str] = []
        self.metrics: CrashMetrics | None = None

    def make_target(self, frame: pd.DataFrame) -> pd.Series:
        def label(group: pd.DataFrame) -> pd.Series:
            close = group["close"].to_numpy(dtype=float)
            y = np.zeros(len(close), dtype=float)
            for i in range(len(close)):
                end = min(len(close), i + self.horizon + 1)
                if end > i + 1:
                    future = close[i + 1:end]
                    peak = np.maximum.accumulate(np.r_[close[i], future])
                    drawdown = future / peak[1:] - 1.0
                    y[i] = float(drawdown.min() <= self.drawdown_threshold)
            return pd.Series(y, index=group.index)
        return frame.groupby("tic", group_keys=False).apply(label).sort_index()

    def fit(self, frame: pd.DataFrame, feature_columns: list[str], train_end: pd.Timestamp | None = None) -> "CrashRiskModel":
        data = frame.copy()
        self.features = [c for c in feature_columns if c in data.columns]
        target = self.make_target(data)
        X = data[self.features].replace([np.inf, -np.inf], np.nan)
        mask = X.notna().all(axis=1) & target.notna()
        if train_end is not None:
            mask &= pd.to_datetime(data["date"]) <= train_end
        X, y = X.loc[mask], target.loc[mask].astype(int)
        if len(X) < 100 or y.nunique() < 2:
            raise ValueError("Crash model needs at least two classes and enough observations.")
        self.model.fit(X, y)
        return self

    def predict_latest(self, frame: pd.DataFrame) -> pd.DataFrame:
        X = frame[self.features].replace([np.inf, -np.inf], np.nan)
        valid = X.notna().all(axis=1)
        out = frame.loc[valid, ["date", "tic"]].copy()
        out["crash_probability"] = self.model.predict_proba(X.loc[valid])[:, 1]
        return out

    def evaluate(self, frame: pd.DataFrame, end: pd.Timestamp) -> CrashMetrics:
        target = self.make_target(frame)
        X = frame[self.features].replace([np.inf, -np.inf], np.nan)
        mask = (pd.to_datetime(frame["date"]) > end) & X.notna().all(axis=1) & target.notna()
        if not mask.any():
            self.metrics = CrashMetrics(self.horizon, self.drawdown_threshold, None, None, None)
            return self.metrics
        y = target.loc[mask].astype(int)
        p = self.model.predict_proba(X.loc[mask])[:, 1]
        pred = (p >= 0.5).astype(int)
        auc = float(roc_auc_score(y, p)) if y.nunique() > 1 else None
        self.metrics = CrashMetrics(self.horizon, self.drawdown_threshold, auc, float(precision_score(y, pred, zero_division=0)), float(recall_score(y, pred, zero_division=0)))
        return self.metrics
