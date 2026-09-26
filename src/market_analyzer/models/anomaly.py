"""Market anomaly and stress signals."""
from __future__ import annotations

import numpy as np
import pandas as pd


def robust_zscore(series: pd.Series, window: int = 60) -> pd.Series:
    median = series.rolling(window).median()
    mad = (series - median).abs().rolling(window).median()
    return (series - median) / (1.4826 * mad + 1e-8)


def compute_market_anomaly_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ret = out.groupby("tic")["return_1d"].transform(lambda s: robust_zscore(s, 60))
    vol = out.groupby("tic")["volume_z_20d"].transform(lambda s: s)
    volat = out.groupby("tic")["volatility_20d"].transform(lambda s: robust_zscore(s, 60))
    turbulence = out.get("turbulence", pd.Series(0.0, index=out.index)).fillna(0.0)

    score = (
        ret.abs().fillna(0.0) * 0.30
        + vol.abs().fillna(0.0) * 0.25
        + volat.abs().fillna(0.0) * 0.25
        + np.log1p(turbulence).clip(lower=0) * 0.20
    )

    out["anomaly_score"] = score
    out["stress_flag"] = out["anomaly_score"] >= out["anomaly_score"].rolling(252).quantile(0.95)
    return out


class MarketAnomalyDetector:
    """Fit a lightweight anomaly scorer and expose the pipeline interface."""

    def __init__(self, window: int = 60):
        self.window = window
        self.feature_columns = []

    def fit(self, df: pd.DataFrame, feature_columns):
        self.feature_columns = list(feature_columns)
        return self

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        return compute_market_anomaly_score(df)[["date", "tic", "anomaly_score", "stress_flag"]]
