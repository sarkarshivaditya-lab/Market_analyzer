from __future__ import annotations

import numpy as np
import pandas as pd

from market_analyzer.backtest.engine import performance_metrics


def _price_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    data = prices.copy()
    data["date"] = pd.to_datetime(data["date"])
    return data.pivot(index="date", columns="tic", values="close").sort_index().ffill()


def _backtest_target_weights(
    px: pd.DataFrame,
    target_weights: pd.DataFrame,
    transaction_cost_bps: float,
    slippage_bps: float,
) -> pd.DataFrame:
    returns = px.pct_change().fillna(0.0)
    target_weights = target_weights.reindex(index=px.index, columns=px.columns).fillna(0.0)
    previous_end = pd.Series(0.0, index=px.columns)
    rows = []
    for dt in px.index:
        target = target_weights.loc[dt].astype(float)
        if target.sum() > 0:
            target = target / target.sum()
        turnover = float((target - previous_end).abs().sum())
        cost = turnover * (transaction_cost_bps + slippage_bps) / 10000.0
        portfolio_return = float((previous_end * returns.loc[dt]).sum() - cost)
        end_values = previous_end * (1.0 + returns.loc[dt])
        if end_values.sum() > 0:
            previous_end = end_values / end_values.sum()
        else:
            previous_end = target.copy()
        rows.append((portfolio_return, turnover, cost))
    out = pd.DataFrame(rows, index=px.index, columns=["return", "turnover", "cost"])
    out["equity"] = (1.0 + out["return"]).cumprod()
    return out


def equal_weight_backtest(
    prices: pd.DataFrame,
    transaction_cost_bps: float = 5.0,
    slippage_bps: float = 2.0,
) -> pd.DataFrame:
    px = _price_matrix(prices)
    if px.empty:
        return pd.DataFrame({"return": [], "turnover": [], "cost": [], "equity": []}, index=px.index)
    weights = pd.DataFrame(1.0 / len(px.columns), index=px.index, columns=px.columns)
    return _backtest_target_weights(px, weights, transaction_cost_bps, slippage_bps)


def buy_and_hold_backtest(
    prices: pd.DataFrame,
    transaction_cost_bps: float = 5.0,
    slippage_bps: float = 2.0,
) -> pd.DataFrame:
    px = _price_matrix(prices)
    if px.empty:
        return pd.DataFrame({"return": [], "turnover": [], "cost": [], "equity": []}, index=px.index)
    weights = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    weights.iloc[0] = 1.0 / len(px.columns)
    return _backtest_target_weights(px, weights, transaction_cost_bps, slippage_bps)


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
        if volatility_scaled:
            vol = returns[selected].rolling(20).std().loc[dt].replace(0.0, np.nan)
            inv = 1.0 / vol
            inv = inv.replace([np.inf, -np.inf], np.nan).dropna()
            if inv.empty:
                continue
            weights.loc[dt, inv.index] = inv / inv.sum()
        else:
            weights.loc[dt, selected] = 1.0 / len(selected)
    return _backtest_target_weights(px, weights, transaction_cost_bps, slippage_bps)


def baseline_report(
    prices: pd.DataFrame,
    transaction_cost_bps: float = 5.0,
    slippage_bps: float = 2.0,
) -> pd.DataFrame:
    strategies = {
        "equal_weight": equal_weight_backtest(prices, transaction_cost_bps, slippage_bps),
        "buy_and_hold": buy_and_hold_backtest(prices, transaction_cost_bps, slippage_bps),
        "momentum_top3": momentum_backtest(prices, top_n=3, transaction_cost_bps=transaction_cost_bps, slippage_bps=slippage_bps),
        "momentum_top3_vol_scaled": momentum_backtest(
            prices,
            top_n=3,
            volatility_scaled=True,
            transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps,
        ),
    }
    rows = []
    for name, bt in strategies.items():
        m = performance_metrics(bt)
        rows.append({"strategy": name, **m})
    return pd.DataFrame(rows)
