from __future__ import annotations

import numpy as np
import pandas as pd

from market_analyzer.backtest.engine import performance_metrics


def _as_datetime_index(series: pd.Series | pd.Index) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(series))


def signal_statistics(signals: pd.DataFrame) -> dict[str, object]:
    if signals.empty:
        return {
            "observations": 0,
            "dates": 0,
            "tickers": 0,
            "positive_signal_observations": 0.0,
            "positive_signal_dates": 0.0,
            "neutral_observations": 0.0,
            "negative_observations": 0.0,
        }
    data = signals.copy()
    data["date"] = pd.to_datetime(data["date"])
    score = pd.to_numeric(data["decision_score"], errors="coerce").fillna(0.0)
    by_date = data.groupby("date")["decision_score"].max().fillna(0.0)
    return {
        "observations": int(len(data)),
        "dates": int(data["date"].nunique()),
        "tickers": int(data["tic"].nunique()),
        "positive_signal_observations": float((score > 0).mean()),
        "positive_signal_dates": float((by_date > 0).mean()),
        "neutral_observations": float((score == 0).mean()),
        "negative_observations": float((score < 0).mean()),
    }


def exposure_statistics(signals: pd.DataFrame, prices: pd.DataFrame) -> dict[str, float]:
    if signals.empty or prices.empty:
        return {"mean_exposure": 0.0, "median_exposure": 0.0, "cash_days": 0, "cash_fraction": 1.0}
    data = signals.copy()
    data["date"] = pd.to_datetime(data["date"])
    score = data.pivot(index="date", columns="tic", values="decision_score").sort_index()
    weights = score.clip(lower=0.0)
    weights = weights.div(weights.sum(axis=1).replace(0.0, np.nan), axis=0).fillna(0.0)
    exposure = weights.sum(axis=1)
    cash = exposure.eq(0.0)
    return {
        "mean_exposure": float(exposure.mean()),
        "median_exposure": float(exposure.median()),
        "cash_days": int(cash.sum()),
        "cash_fraction": float(cash.mean()),
    }


def turnover_statistics(backtest: pd.DataFrame) -> dict[str, float]:
    if backtest.empty:
        return {"mean_daily_turnover": 0.0, "median_daily_turnover": 0.0, "total_turnover": 0.0, "mean_daily_cost": 0.0, "total_cost": 0.0}
    turnover = pd.to_numeric(backtest["turnover"], errors="coerce").fillna(0.0)
    cost = pd.to_numeric(backtest["cost"], errors="coerce").fillna(0.0)
    return {
        "mean_daily_turnover": float(turnover.mean()),
        "median_daily_turnover": float(turnover.median()),
        "total_turnover": float(turnover.sum()),
        "mean_daily_cost": float(cost.mean()),
        "total_cost": float(cost.sum()),
    }


def fold_report(backtest: pd.DataFrame, benchmark_returns: pd.Series, fold_size: int = 63) -> pd.DataFrame:
    if backtest.empty:
        return pd.DataFrame(columns=[
            "fold", "start", "end", "strategy_return", "benchmark_return",
            "excess_return", "strategy_sharpe", "benchmark_sharpe",
            "strategy_hit_rate", "benchmark_hit_rate", "strategy_turnover",
            "strategy_cost", "observations",
        ])
    data = backtest.copy()
    data.index = _as_datetime_index(data.index)
    benchmark = pd.Series(benchmark_returns, dtype=float).copy()
    benchmark.index = _as_datetime_index(benchmark.index)
    benchmark = benchmark.reindex(data.index).fillna(0.0)
    rows: list[dict[str, object]] = []
    for fold, start in enumerate(range(0, len(data), fold_size), start=1):
        end = min(start + fold_size, len(data))
        if end - start < 10:
            continue
        sr = pd.Series(data["return"].iloc[start:end], dtype=float)
        br = benchmark.iloc[start:end]
        sm = performance_metrics(data.iloc[start:end])
        bm = performance_metrics(pd.DataFrame({
            "return": br,
            "turnover": 0.0,
            "cost": 0.0,
            "equity": (1.0 + br).cumprod(),
        }))
        rows.append({
            "fold": fold,
            "start": data.index[start],
            "end": data.index[end - 1],
            "strategy_return": float((1.0 + sr).prod() - 1.0),
            "benchmark_return": float((1.0 + br).prod() - 1.0),
            "excess_return": float((1.0 + sr).prod() - (1.0 + br).prod()),
            "strategy_sharpe": float(sm["sharpe"]),
            "benchmark_sharpe": float(bm["sharpe"]),
            "strategy_hit_rate": float((sr > 0).mean()),
            "benchmark_hit_rate": float((br > 0).mean()),
            "strategy_turnover": float(data["turnover"].iloc[start:end].sum()),
            "strategy_cost": float(data["cost"].iloc[start:end].sum()),
            "observations": int(end - start),
        })
    return pd.DataFrame(rows)


def base_forecaster_report(base_forecasts: pd.DataFrame, prices: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    if base_forecasts.empty:
        return pd.DataFrame()
    data = base_forecasts.copy()
    data["date"] = pd.to_datetime(data["date"])
    px = prices.copy()
    px["date"] = pd.to_datetime(px["date"])
    close = px.sort_values(["tic", "date"]).copy()
    close["future_return"] = close.groupby("tic")["close"].shift(-horizon) / close["close"] - 1.0
    data = data.merge(close[["date", "tic", "future_return"]], on=["date", "tic"], how="left")
    rows = []
    for hcol in sorted([c for c in data.columns if c.startswith("expected_return_")]):
        h = hcol.removeprefix("expected_return_")
        pred = pd.to_numeric(data[hcol], errors="coerce")
        y = pd.to_numeric(data["future_return"], errors="coerce")
        mask = pred.notna() & y.notna()
        if not mask.any():
            continue
        p, t = pred.loc[mask], y.loc[mask]
        direction = np.sign(p)
        actual = np.sign(t)
        rows.append({
            "forecaster": hcol,
            "horizon": h,
            "observations": int(mask.sum()),
            "mae": float(np.abs(p - t).mean()),
            "rmse": float(np.sqrt(((p - t) ** 2).mean())),
            "directional_accuracy": float((direction == actual).mean()),
            "mean_predicted_return": float(p.mean()),
            "mean_realized_return": float(t.mean()),
        })
    return pd.DataFrame(rows)


def build_research_diagnostics(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    backtest: pd.DataFrame,
    benchmark_returns: pd.Series | None = None,
    base_forecasts: pd.DataFrame | None = None,
    fold_size: int = 63,
) -> dict[str, object]:
    benchmark_returns = pd.Series(benchmark_returns, dtype=float) if benchmark_returns is not None else pd.Series(dtype=float)
    result: dict[str, object] = {
        "signals": signal_statistics(signals),
        "exposure": exposure_statistics(signals, prices),
        "turnover": turnover_statistics(backtest),
        "strategy_metrics": performance_metrics(backtest) if not backtest.empty else {},
    }
    if not benchmark_returns.empty:
        result["folds"] = fold_report(backtest, benchmark_returns, fold_size=fold_size).to_dict("records")
    else:
        result["folds"] = []
    if base_forecasts is not None:
        result["base_forecasters"] = base_forecaster_report(base_forecasts, prices).to_dict("records")
    else:
        result["base_forecasters"] = []
    return result
