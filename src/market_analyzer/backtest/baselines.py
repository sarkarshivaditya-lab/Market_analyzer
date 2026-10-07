from __future__ import annotations

import numpy as np
import pandas as pd

from market_analyzer.backtest.engine import performance_metrics


def _price_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    data = prices.copy()
    data["date"] = pd.to_datetime(data["date"])
    return data.pivot(index="date", columns="tic", values="close").sort_index().ffill()


def equal_weight_backtest(prices: pd.DataFrame, transaction_cost_bps: float = 5.0, slippage_bps: float = 2.0) -> pd.DataFrame:
    px = _price_matrix(prices)
    returns = px.pct_change().fillna(0.0)
    weights = pd.DataFrame(1.0 / len(px.columns), index=px.index, columns=px.columns) if len(px.columns) else pd.DataFrame(index=px.index)
    held = weights.shift(1).fillna(0.0)
    turnover = (weights - held).abs().sum(axis=1)
    cost = turnover * (transaction_cost_bps + slippage_bps) / 10000.0
    portfolio_return = (held * returns).sum(axis=1) - cost
    return pd.DataFrame({"return": portfolio_return, "turnover": turnover, "cost": cost, "equity": (1.0 + portfolio_return).cumprod()})


def buy_and_hold_backtest(prices: pd.DataFrame, transaction_cost_bps: float = 5.0, slippage_bps: float = 2.0) -> pd.DataFrame:
    return equal_weight_backtest(prices, transaction_cost_bps=transaction_cost_bps, slippage_bps=slippage_bps)


def momentum_backtest(
    prices: pd.DataFrame,
    lookback: int = 126,
    top_n: int | None = 3,
    volatility_scaled: bool = False,
    transaction_cost_bps: float = 5.0,
    slippage_bps: float = 2.0,
) -> pd.DataFrame:
    px = _price_matrix(prices)
    returns = px.pct_change().fillna(0.0)
    momentum = px.pct_change(lookback)
    weights = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    for dt in px.index:
        scores = momentum.loc[dt].dropna()
        if scores.empty:
            continue
        if top_n is not None:
            selected = scores.nlargest(min(top_n, len(scores))).index
        else:
            selected = scores.index
        w = pd.Series(0.0, index=px.columns)
        if volatility_scaled:
            vol = returns[selected].rolling(20).std().loc[dt].replace(0.0, np.nan)
            inv = 1.0 / vol
            inv = inv.replace([np.inf, -np.inf], np.nan).dropna()
            if inv.empty:
                continue
            w.loc[inv.index] = inv / inv.sum()
        else:
            w.loc[selected] = 1.0 / len(selected)
        weights.loc[dt] = w
    held = weights.shift(1).fillna(0.0)
    turnover = (weights - held).abs().sum(axis=1)
    cost = turnover * (transaction_cost_bps + slippage_bps) / 10000.0
    portfolio_return = (held * returns).sum(axis=1) - cost
    return pd.DataFrame({"return": portfolio_return, "turnover": turnover, "cost": cost, "equity": (1.0 + portfolio_return).cumprod()})


def baseline_report(prices: pd.DataFrame, transaction_cost_bps: float = 5.0, slippage_bps: float = 2.0) -> pd.DataFrame:
    strategies = {
        "equal_weight": equal_weight_backtest(prices, transaction_cost_bps, slippage_bps),
        "momentum_top3": momentum_backtest(prices, top_n=3, transaction_cost_bps=transaction_cost_bps, slippage_bps=slippage_bps),
        "momentum_top3_vol_scaled": momentum_backtest(prices, top_n=3, volatility_scaled=True, transaction_cost_bps=transaction_cost_bps, slippage_bps=slippage_bps),
    }
    rows = []
    for name, bt in strategies.items():
        m = performance_metrics(bt)
        rows.append({"strategy": name, **m})
    return pd.DataFrame(rows)
