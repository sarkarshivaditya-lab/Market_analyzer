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
