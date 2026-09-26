import numpy as np
import pandas as pd
from market_analyzer.backtest.engine import signal_backtest, performance_metrics

def test_signal_backtest_generates_metrics():
    dates=pd.date_range("2025-01-01",periods=30,freq="D")
    prices=pd.DataFrame({
        "date":list(dates)*2,
        "tic":["SPY"]*30+["TLT"]*30,
        "close":list(np.linspace(100,110,30))+list(np.linspace(100,102,30)),
    })
    signals=pd.DataFrame({
        "date":list(dates)*2,
        "tic":["SPY"]*30+["TLT"]*30,
        "decision_score":[.7]*30+[.3]*30,
    })
    bt=signal_backtest(signals,prices,transaction_cost_bps=5,slippage_bps=2)
    metrics=performance_metrics(bt)
    assert len(bt)==30
    assert np.isfinite(metrics["cagr"])
    assert np.isfinite(metrics["max_drawdown"])
    assert metrics["total_cost"]>=0

def test_backtest_keeps_costs_separate_from_returns():
    dates=pd.date_range("2025-01-01",periods=10,freq="D")
    prices=pd.DataFrame({"date":list(dates)*2,"tic":["SPY"]*10+["TLT"]*10,"close":100.0})
    signals=pd.DataFrame({"date":list(dates)*2,"tic":["SPY"]*10+["TLT"]*10,"decision_score":[1.0]*20})
    bt=signal_backtest(signals,prices,transaction_cost_bps=10,slippage_bps=5)
    assert float(bt["cost"].sum())>=0
    assert np.isfinite(bt["return"]).all()
