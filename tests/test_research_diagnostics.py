import numpy as np
import pandas as pd

from market_analyzer.backtest.baselines import buy_and_hold_backtest, equal_weight_backtest, momentum_backtest
from market_analyzer.backtest.diagnostics import (
    base_forecaster_report,
    build_research_diagnostics,
    fold_report,
    signal_statistics,
)


def _prices():
    dates = pd.date_range("2020-01-01", periods=40, freq="D")
    rows = []
    for tic, scale in [("A", 1.0), ("B", 1.2), ("C", 0.9)]:
        for i, dt in enumerate(dates):
            rows.append({"date": dt, "tic": tic, "close": scale * (1 + 0.001 * i)})
    return pd.DataFrame(rows)


def _signals():
    p = _prices()
    out = p[["date", "tic"]].copy()
    out["decision_score"] = np.where(out["tic"].eq("A"), 0.01, -0.01)
    return out


def test_signal_statistics():
    stats = signal_statistics(_signals())
    assert stats["observations"] == 120
    assert 0 < stats["positive_signal_observations"] < 1


def test_fold_report():
    bt = equal_weight_backtest(_prices())
    bench = bt["return"].copy()
    report = fold_report(bt, bench, fold_size=20)
    assert len(report) == 2
    assert {"strategy_return", "benchmark_return", "strategy_turnover"}.issubset(report.columns)


def test_momentum_runs():
    bt = momentum_backtest(_prices(), lookback=5, top_n=2)
    assert len(bt) == 40
    assert np.isfinite(bt["return"]).all()


def test_base_forecaster_report():
    p = _prices()
    f = p[["date", "tic"]].copy()
    f["expected_return_5d"] = 0.005
    out = base_forecaster_report(f, p, horizon=5)
    assert not out.empty
    assert out.iloc[0]["observations"] > 0


def test_build_diagnostics():
    bt = equal_weight_backtest(_prices())
    d = build_research_diagnostics(_signals(), _prices(), bt, bt["return"])
    assert "folds" in d
    assert "turnover" in d


def test_buy_and_hold_has_no_rebalancing_turnover():
    bt = buy_and_hold_backtest(_prices())
    assert bt["turnover"].iloc[0] == 1.0
    assert bt["turnover"].iloc[1:].sum() == 0.0


def test_base_forecaster_report_uses_each_horizon():
    p = _prices()
    f = p[["date", "tic"]].copy()
    f["expected_return_1d"] = 0.001
    f["expected_return_5d"] = 0.005
    f["expected_return_20d"] = 0.02
    out = base_forecaster_report(f, p)
    assert set(out["horizon"]) == {1, 5, 20}
    assert out.loc[out["horizon"] == 1, "observations"].iloc[0] > out.loc[out["horizon"] == 20, "observations"].iloc[0]
