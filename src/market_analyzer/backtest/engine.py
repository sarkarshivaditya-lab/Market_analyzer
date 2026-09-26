from __future__ import annotations
import numpy as np
import pandas as pd

def signal_backtest(signals,prices,transaction_cost_bps=5.0,slippage_bps=2.0):
    px=prices.pivot(index="date",columns="tic",values="close").sort_index().ffill()
    score=signals.pivot(index="date",columns="tic",values="decision_score").reindex(px.index).fillna(0.0)
    weights=score.clip(lower=0.0)
    weights=weights.div(weights.sum(axis=1).replace(0,np.nan),axis=0).fillna(0.0)
    returns=px.pct_change().fillna(0.0)
    held=weights.shift(1).fillna(0.0)
    turnover=(weights-held).abs().sum(axis=1)
    cost=turnover*(transaction_cost_bps+slippage_bps)/10000.0
    portfolio_return=(held*returns).sum(axis=1)-cost
    return pd.DataFrame({"return":portfolio_return,"turnover":turnover,"cost":cost,"equity":(1+portfolio_return).cumprod()})

def performance_metrics(backtest,annualization=252):
    r=backtest["return"].astype(float); equity=backtest["equity"].astype(float)
    years=max(len(r)/annualization,1/annualization)
    vol=float(r.std(ddof=1)*np.sqrt(annualization))
    sharpe=float(r.mean()/r.std(ddof=1)*np.sqrt(annualization)) if r.std(ddof=1) else 0.0
    downside=r[r<0].std(ddof=1)
    sortino=float(r.mean()/downside*np.sqrt(annualization)) if downside and not np.isnan(downside) else 0.0
    dd=equity/equity.cummax()-1
    return {"cagr":float(equity.iloc[-1]**(1/years)-1),"volatility":vol,"sharpe":sharpe,"sortino":sortino,"max_drawdown":float(dd.min()),"total_turnover":float(backtest["turnover"].sum()),"total_cost":float(backtest["cost"].sum())}

def walk_forward_dates(dates,min_train_days=756,test_step_days=21):
    dates=pd.Series(pd.to_datetime(dates).drop_duplicates().sort_values().tolist())
    for i in range(min_train_days,len(dates),test_step_days):
        train_end=dates.iloc[i-1]; test_end=dates.iloc[min(i+test_step_days-1,len(dates)-1)]
        yield train_end,test_end
