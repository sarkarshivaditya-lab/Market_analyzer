from __future__ import annotations

import numpy as np
import pandas as pd


def equity_metrics(returns: pd.Series) -> dict[str, float]:
    r = pd.Series(returns, dtype=float).fillna(0.0)
    equity = (1.0 + r).cumprod()
    years = max(len(r) / 252.0, 1 / 252.0)
    total = float(equity.iloc[-1] - 1.0) if len(equity) else 0.0
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if len(equity) else 0.0
    vol = float(r.std(ddof=1) * np.sqrt(252.0)) if len(r) > 1 else 0.0
    sharpe = float(r.mean() / r.std(ddof=1) * np.sqrt(252.0)) if r.std(ddof=1) > 0 else 0.0
    downside = r.where(r < 0, 0.0).std(ddof=1)
    sortino = float(r.mean() / downside * np.sqrt(252.0)) if downside and downside > 0 else 0.0
    peak = equity.cummax()
    dd = equity / peak - 1.0
    max_dd = float(dd.min()) if len(dd) else 0.0
    calmar = float(cagr / abs(max_dd)) if max_dd < 0 else 0.0
    return {
        "total_return": total, "cagr": cagr, "volatility": vol,
        "sharpe": sharpe, "sortino": sortino, "max_drawdown": max_dd,
        "calmar": calmar, "hit_rate": float((r > 0).mean()),
        "worst_day": float(r.min()) if len(r) else 0.0,
    }


def benchmark_returns(prices: pd.DataFrame, benchmark: str = "SPY") -> pd.Series:
    if benchmark not in prices.columns:
        raise ValueError(f"Benchmark {benchmark} is not present.")
    return prices[benchmark].pct_change().fillna(0.0)


def compare_strategy_to_benchmark(strategy_returns: pd.Series, prices: pd.DataFrame,
                                   benchmark: str = "SPY") -> dict[str, dict[str, float]]:
    bench = benchmark_returns(prices, benchmark).reindex(strategy_returns.index).fillna(0.0)
    return {"strategy": equity_metrics(strategy_returns), "benchmark": equity_metrics(bench)}


def rolling_forward_performance(returns: pd.Series, window: int = 63) -> pd.DataFrame:
    r = pd.Series(returns, dtype=float).fillna(0.0)
    return pd.DataFrame({
        "rolling_return": r.rolling(window).apply(lambda x: np.prod(1.0 + x) - 1.0, raw=True),
        "rolling_volatility": r.rolling(window).std() * np.sqrt(252.0),
        "rolling_sharpe": r.rolling(window).mean() / r.rolling(window).std().replace(0, np.nan) * np.sqrt(252.0),
    })


def walk_forward_report(strategy_returns: pd.Series, benchmark_returns_: pd.Series,
                        fold_size: int = 63) -> pd.DataFrame:
    rows = []
    n = len(strategy_returns)
    for start in range(0, n, fold_size):
        end = min(start + fold_size, n)
        if end - start < 10:
            continue
        sr = strategy_returns.iloc[start:end]
        br = benchmark_returns_.iloc[start:end]
        sm = equity_metrics(sr)
        bm = equity_metrics(br)
        rows.append({
            "start": strategy_returns.index[start],
            "end": strategy_returns.index[end - 1],
            "strategy_return": sm["total_return"],
            "benchmark_return": bm["total_return"],
            "excess_return": sm["total_return"] - bm["total_return"],
            "strategy_sharpe": sm["sharpe"],
            "benchmark_sharpe": bm["sharpe"],
        })
    return pd.DataFrame(rows)
