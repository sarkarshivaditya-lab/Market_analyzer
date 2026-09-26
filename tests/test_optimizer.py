import numpy as np
import pandas as pd
from market_analyzer.risk.optimizer import PortfolioOptimizer

def test_optimizer_respects_long_only_and_cap():
    rng = np.random.default_rng(2)
    returns = pd.DataFrame(rng.normal(0, .01, (300, 4)), columns=list("ABCD"))
    mu = pd.Series([.08, .06, .04, .02], index=list("ABCD"))
    w = PortfolioOptimizer().optimize(mu, returns)
    assert np.isclose(w.sum(), 1.0)
    assert (w >= 0).all()
    assert (w <= .35 + 1e-9).all()

import pytest
from market_analyzer.risk.optimizer import PortfolioConstraints

def test_optimizer_rejects_infeasible_max_weight():
    expected = pd.Series({"A": 0.1, "B": 0.1})
    returns = pd.DataFrame(np.zeros((20, 2)), columns=["A", "B"])
    with pytest.raises(ValueError, match="infeasible"):
        PortfolioOptimizer(PortfolioConstraints(max_weight=0.4)).optimize(expected, returns)


def test_optimizer_labels_asset_index_for_portfolio_merge():
    rng = np.random.default_rng(7)
    returns = pd.DataFrame(rng.normal(0, .01, (300, 4)), columns=list("ABCD"))
    mu = pd.Series([.08, .06, .04, .02], index=list("ABCD"))
    w = PortfolioOptimizer().optimize(mu, returns)
    frame = w.rename("target_weight").reset_index()
    assert list(frame.columns) == ["tic", "target_weight"]
    assert set(frame["tic"]) == set("ABCD")


def test_optimizer_can_use_risk_adjusted_expected_returns():
    rng = np.random.default_rng(11)
    returns = pd.DataFrame(rng.normal(0, .01, (300, 3)), columns=["SAFE", "RISKY", "MID"])
    raw = pd.Series({"SAFE": .04, "RISKY": .10, "MID": .06})
    risk_adjusted = pd.Series({"SAFE": .04, "RISKY": .01, "MID": .03})
    optimizer = PortfolioOptimizer()
    raw_weights = optimizer.optimize(raw, returns)
    adjusted_weights = optimizer.optimize(risk_adjusted, returns)
    assert adjusted_weights["SAFE"] >= raw_weights["SAFE"] - 1e-9

def test_optimizer_can_retain_cash_with_cash_allowed():
    rng = np.random.default_rng(13)
    returns = pd.DataFrame(rng.normal(0, .01, (300, 3)), columns=["A","B","C"])
    mu = pd.Series([0.0, 0.0, 0.0], index=["A","B","C"])
    weights = PortfolioOptimizer().optimize(mu, returns, allow_cash=True)
    assert (weights >= 0).all()
    assert (weights <= .35 + 1e-9).all()
    assert weights.sum() <= 1.0 + 1e-9
