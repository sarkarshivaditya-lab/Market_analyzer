import numpy as np
import pandas as pd
from market_analyzer.backtest.engine import performance_metrics,signal_backtest,walk_forward_dates
from market_analyzer.models.crash import CrashRiskModel

def sample_prices(n=160):
    dates=pd.date_range("2020-01-01",periods=n,freq="B"); rows=[]
    for tic,base in [("AAA",100),("BBB",80)]:
        close=base*np.cumprod(1+np.random.default_rng(1).normal(.0003,.01,n))
        for d,p in zip(dates,close):
            rows.append({"date":d,"tic":tic,"open":p,"high":p*1.01,"low":p*.99,"close":p,"volume":100000})
    return pd.DataFrame(rows)

def test_crash_target_shape():
    data=sample_prices(); y=CrashRiskModel(horizon=20).make_target(data)
    assert len(y)==len(data); assert set(y.unique()).issubset({0,1})

def test_backtest_metrics():
    prices=sample_prices(); signals=prices[["date","tic"]].copy(); signals["decision_score"]=1.0
    metrics=performance_metrics(signal_backtest(signals,prices))
    assert np.isfinite(metrics["cagr"]) and "max_drawdown" in metrics

def test_walk_forward():
    dates=pd.date_range("2020-01-01",periods=1000,freq="B")
    windows=list(walk_forward_dates(dates,756,21))
    assert windows and windows[0][0]<windows[0][1]
