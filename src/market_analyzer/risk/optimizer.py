from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass
class PortfolioConstraints:
    max_weight: float = 0.35
    target_volatility: float = 0.15
    risk_aversion: float = 5.0
    turnover_penalty: float = 0.002


class PortfolioOptimizer:
    """Long-only, covariance-aware optimizer with concentration and turnover controls."""

    def __init__(self, constraints: PortfolioConstraints | None = None):
        self.constraints = constraints or PortfolioConstraints()

    def optimize(self, expected_returns: pd.Series, returns: pd.DataFrame,
                 previous_weights: pd.Series | None = None) -> pd.Series:
        assets = [a for a in expected_returns.index if a in returns.columns]
        if not assets:
            return pd.Series(dtype=float)
        mu = expected_returns.loc[assets].astype(float).fillna(0.0).to_numpy()
        hist = returns[assets].astype(float).replace([np.inf, -np.inf], np.nan).dropna(how="all")
        cov = hist.cov().fillna(0.0).to_numpy()
        if cov.shape != (len(assets), len(assets)):
            cov = np.eye(len(assets)) * 0.0001
        cov += np.eye(len(assets)) * 1e-8
        prev = np.zeros(len(assets))
        if previous_weights is not None:
            prev = previous_weights.reindex(assets).fillna(0.0).to_numpy()

        def objective(w):
            variance = float(w @ cov @ w)
            turnover = float(np.abs(w - prev).sum())
            return -(w @ mu) + self.constraints.risk_aversion * variance + self.constraints.turnover_penalty * turnover

        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, self.constraints.max_weight)] * len(assets)
        x0 = np.ones(len(assets)) / len(assets)
        x0 = np.minimum(x0, self.constraints.max_weight)
        x0 /= x0.sum()
        result = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=cons,
                          options={"maxiter": 500, "ftol": 1e-10})
        if not result.success:
            return pd.Series(x0, index=assets)
        weights = pd.Series(np.clip(result.x, 0.0, self.constraints.max_weight), index=assets)
        return weights / weights.sum()

    @staticmethod
    def portfolio_volatility(weights: pd.Series, returns: pd.DataFrame) -> float:
        cols = [c for c in weights.index if c in returns.columns]
        cov = returns[cols].cov().fillna(0.0)
        w = weights[cols].to_numpy()
        return float(np.sqrt(max(w @ cov.to_numpy() @ w, 0.0)) * np.sqrt(252.0))
