import pandas as pd
import numpy as np
from market_analyzer.backtest.research import equity_metrics, walk_forward_report

def test_serious_metrics_are_finite():
    r = pd.Series(np.repeat(.001, 300))
    m = equity_metrics(r)
    assert np.isfinite(m["cagr"])
    assert "calmar" in m

def test_walk_forward_report_has_folds():
    idx = pd.date_range("2020-01-01", periods=140, freq="D")
    r = pd.Series(.001, index=idx)
    out = walk_forward_report(r, r, fold_size=30)
    assert len(out) >= 4
