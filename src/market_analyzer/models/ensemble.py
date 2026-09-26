from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, roc_auc_score


@dataclass
class EnsembleMetrics:
    mae: float | None
    auc: float | None
    observations: int


class IntelligenceEnsemble:
    """Leakage-aware meta-model over base-model forecasts and risk/context signals."""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.features: list[str] = []
        self.regressor = HistGradientBoostingRegressor(
            max_iter=250, learning_rate=0.04, max_leaf_nodes=15,
            l2_regularization=1.0, random_state=random_state
        )
        self.classifier = HistGradientBoostingClassifier(
            max_iter=250, learning_rate=0.04, max_leaf_nodes=15,
            l2_regularization=1.0, random_state=random_state
        )
        self.metrics = EnsembleMetrics(None, None, 0)
        self.fitted = False

    @staticmethod
    def target(frame: pd.DataFrame, horizon: int = 5) -> pd.Series:
        data = frame.sort_values(["tic", "date"])
        y = data.groupby("tic")["close"].transform(lambda s: s.shift(-horizon) / s - 1.0)
        return y.reindex(frame.index)

    @staticmethod
    def feature_columns(frame: pd.DataFrame) -> list[str]:
        preferred = [
            "expected_return_1d", "expected_return_5d", "expected_return_20d",
            "crash_probability", "regime_probability", "anomaly_score",
            "return_1d", "return_5d", "return_20d", "volatility_20d",
            "volatility_60d", "drawdown_60d", "turbulence",
            "macro_vix", "macro_vix_chg_5d", "macro_vix_z_60d",
            "macro_tnx", "macro_tnx_chg_20d",
            "macro_dx_y_nyb_chg_5d", "macro_gc_f_chg_5d", "macro_cl_f_chg_5d",
            "breadth_pct_positive_1d", "breadth_pct_positive_5d",
            "breadth_median_return_1d", "breadth_median_return_5d",
            "market_return_dispersion_1d", "market_return_dispersion_5d",
            "market_cross_sectional_range_1d", "sector_leader_return_20d",
            "sector_laggard_return_20d", "sector_dispersion_20d",
            "relative_return_20d_vs_spy", "relative_volatility_vs_spy",
            "fund_revenue", "fund_net_income", "fund_assets", "fund_liabilities", "fund_equity", "fund_cash",
            "fund_revenue_growth", "fund_net_income_growth", "fund_profit_margin", "fund_debt_to_assets",
            "fund_equity_ratio", "fund_cash_to_assets",
            "fund_revenue_log", "fund_net_income_log", "fund_assets_log", "fund_liabilities_log",
            "fund_equity_log", "fund_cash_log",
            "news_count", "news_sentiment", "news_sentiment_3d", "news_sentiment_7d", "news_count_3d", "news_count_7d",
        ]
        return [c for c in preferred if c in frame.columns]

    def fit(self, frame: pd.DataFrame, feature_columns: list[str] | None = None) -> "IntelligenceEnsemble":
        data = frame.copy()
        self.features = feature_columns or self.feature_columns(data)
        if not self.features:
            raise ValueError("No ensemble features supplied.")
        target = pd.to_numeric(data["ensemble_target"], errors="coerce")
        X = data[self.features].replace([np.inf, -np.inf], np.nan)
        mask = X.notna().all(axis=1) & target.notna()
        X, y = X.loc[mask], target.loc[mask]
        if len(X) < 200:
            raise ValueError("Ensemble needs at least 200 leakage-safe training observations.")
        self.regressor.fit(X, y)
        self.classifier.fit(X, (y > 0).astype(int))
        self.fitted = True
        self.metrics = EnsembleMetrics(None, None, len(X))
        return self

    def evaluate(self, frame: pd.DataFrame) -> EnsembleMetrics:
        if not self.fitted:
            raise RuntimeError("Fit the ensemble before evaluation.")
        data = frame.copy()
        target = pd.to_numeric(data["ensemble_target"], errors="coerce")
        X = data[self.features].replace([np.inf, -np.inf], np.nan)
        mask = X.notna().all(axis=1) & target.notna()
        if not mask.any():
            return EnsembleMetrics(None, None, 0)
        y = target.loc[mask]
        pred = self.regressor.predict(X.loc[mask])
        prob = self.classifier.predict_proba(X.loc[mask])[:, 1]
        auc = float(roc_auc_score((y > 0).astype(int), prob)) if y.nunique() > 1 else None
        self.metrics = EnsembleMetrics(float(mean_absolute_error(y, pred)), auc, len(y))
        return self.metrics

    def predict(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self.fitted:
            raise RuntimeError("Fit the ensemble before prediction.")
        X = frame[self.features].replace([np.inf, -np.inf], np.nan)
        valid = X.notna().all(axis=1)
        out = frame.loc[valid, ["date", "tic"]].copy()
        out["ensemble_expected_return"] = self.regressor.predict(X.loc[valid])
        out["positive_return_probability"] = self.classifier.predict_proba(X.loc[valid])[:, 1]
        out["ensemble_confidence"] = np.clip(
            np.abs(out["positive_return_probability"] - 0.5) * 2.0, 0.0, 1.0
        )
        return out.sort_values(["date", "tic"]).reset_index(drop=True)
