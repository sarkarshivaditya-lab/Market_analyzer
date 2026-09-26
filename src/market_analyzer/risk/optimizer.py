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
                 previous_weights: pd.Series | None = None, allow_cash: bool = False) -> pd.Series:
        assets = [a for a in expected_returns.index if a in returns.columns]
        if not assets:
            return pd.Series(dtype=float, name="target_weight").rename_axis("tic")
        if len(assets) * self.constraints.max_weight < 1.0:
            raise ValueError("Portfolio constraints are infeasible: max_weight is too small for the number of assets.")
        mu = expected_returns.loc[assets].astype(float).fillna(0.0).to_numpy()
        hist = returns[assets].astype(float).replace([np.inf, -np.inf], np.nan).dropna(how="all")
        cov = hist.cov().fillna(0.0).to_numpy(copy=True)
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

        def annualized_vol(w):
            return float(np.sqrt(max(w @ cov @ w, 0.0)) * np.sqrt(252.0))

        cons = [
            {"type": "ineq" if allow_cash else "eq", "fun": (lambda w: 1.0 - np.sum(w)) if allow_cash else (lambda w: np.sum(w) - 1.0)},
            {"type": "ineq", "fun": lambda w: self.constraints.target_volatility - annualized_vol(w)},
        ]
        bounds = [(0.0, self.constraints.max_weight)] * len(assets)
        x0 = np.zeros(len(assets))
        remaining = 1.0
        for i in range(len(assets)):
            x0[i] = min(self.constraints.max_weight, remaining)
            remaining -= x0[i]
            if remaining <= 0:
                break
        result = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=cons,
                          options={"maxiter": 500, "ftol": 1e-10})
        if not result.success:
            # Preserve the hard concentration constraint even if the volatility target is infeasible.
            fallback=np.zeros(len(assets)) if allow_cash else x0
            return pd.Series(fallback, index=assets, name="target_weight").rename_axis("tic")
        weights = pd.Series(np.clip(result.x, 0.0, self.constraints.max_weight), index=assets)
        if allow_cash:
            return weights.rename_axis("tic")
        return (weights / weights.sum()).rename_axis("tic")

    @staticmethod
    def portfolio_volatility(weights: pd.Series, returns: pd.DataFrame) -> float:
        cols = [c for c in weights.index if c in returns.columns]
        cov = returns[cols].cov().fillna(0.0)
        w = weights[cols].to_numpy()
        return float(np.sqrt(max(w @ cov.to_numpy() @ w, 0.0)) * np.sqrt(252.0))
