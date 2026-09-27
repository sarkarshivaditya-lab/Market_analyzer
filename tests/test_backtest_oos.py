import pandas as pd

from market_analyzer.backtest.engine import signal_backtest


def test_signal_backtest_uses_supplied_oos_signal_dates_only():
    prices = pd.DataFrame([
        {"date":"2026-01-01","tic":"AAA","close":100.0},
        {"date":"2026-01-02","tic":"AAA","close":110.0},
        {"date":"2026-01-03","tic":"AAA","close":121.0},
        {"date":"2026-01-04","tic":"AAA","close":108.9},
    ])
    signals = pd.DataFrame([
        {"date":"2026-01-02","tic":"AAA","decision_score":1.0},
        {"date":"2026-01-03","tic":"AAA","decision_score":0.0},
    ])
    out = signal_backtest(signals, prices)
    assert out.loc[pd.Timestamp("2026-01-02"), "return"] == 0.0
    assert out.loc[pd.Timestamp("2026-01-03"), "return"] == 0.10
    assert out.loc[pd.Timestamp("2026-01-04"), "return"] == 0.0
