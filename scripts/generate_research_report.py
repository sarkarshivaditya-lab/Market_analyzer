from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from market_analyzer.backtest.baselines import (
    buy_and_hold_backtest,
    equal_weight_backtest,
    momentum_backtest,
)
from market_analyzer.backtest.diagnostics import (
    base_forecaster_report,
    build_research_diagnostics,
)
from market_analyzer.backtest.engine import performance_metrics, signal_backtest
from market_analyzer.data.yahoo import YahooMarketData
from market_analyzer.main import run


COST_BPS = 5.0
SLIPPAGE_BPS = 2.0


def _slice_prices(prices: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    data = prices.copy()
    data["date"] = pd.to_datetime(data["date"])
    return data[(data["date"] >= start) & (data["date"] <= end)].copy()


def _forecast_backtest(
    forecasts: pd.DataFrame,
    prices: pd.DataFrame,
    column: str,
) -> pd.DataFrame:
    signals = forecasts[["date", "tic", column]].copy()
    signals = signals.rename(columns={column: "decision_score"})
    return signal_backtest(
        signals,
        prices,
        transaction_cost_bps=COST_BPS,
        slippage_bps=SLIPPAGE_BPS,
    )


def _benchmark_returns(start: pd.Timestamp, end: pd.Timestamp, index: pd.DatetimeIndex) -> pd.Series:
    market = YahooMarketData(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), ["^NSEI"]).fetch()
    market["date"] = pd.to_datetime(market["date"])
    prices = market.pivot(index="date", columns="tic", values="close").rename(columns={"^NSEI": "NIFTY50"})
    return prices["NIFTY50"].pct_change().reindex(index).fillna(0.0)


def _metric_row(name: str, backtest: pd.DataFrame) -> dict[str, object]:
    return {"strategy": name, **performance_metrics(backtest)}


def build_research_report(result: dict[str, object]) -> dict[str, object]:
    oos = result["ensemble_oos_predictions"].copy()
    oos["date"] = pd.to_datetime(oos["date"])
    prices = result["features"][["date", "tic", "close"]].copy()
    prices["date"] = pd.to_datetime(prices["date"])
    start = oos["date"].min()
    end = oos["date"].max()
    prices = _slice_prices(prices, start, end)

    oos_signals = result["oos_signals"].copy()
    oos_signals["date"] = pd.to_datetime(oos_signals["date"])
    ensemble_bt = signal_backtest(
        oos_signals,
        prices,
        transaction_cost_bps=COST_BPS,
        slippage_bps=SLIPPAGE_BPS,
    )
    benchmark = _benchmark_returns(start, end, ensemble_bt.index)

    baseline_inputs = {
        "NIFTY50": None,
        "equal_weight": equal_weight_backtest(prices, COST_BPS, SLIPPAGE_BPS),
        "buy_and_hold": buy_and_hold_backtest(prices, COST_BPS, SLIPPAGE_BPS),
        "momentum_top3": momentum_backtest(prices, top_n=3, transaction_cost_bps=COST_BPS, slippage_bps=SLIPPAGE_BPS),
        "momentum_top3_vol_scaled": momentum_backtest(
            prices,
            top_n=3,
            volatility_scaled=True,
            transaction_cost_bps=COST_BPS,
            slippage_bps=SLIPPAGE_BPS,
        ),
    }

    performance = [_metric_row("ensemble_oos", ensemble_bt)]
    for name, bt in baseline_inputs.items():
        if bt is not None:
            performance.append(_metric_row(name, bt))
    benchmark_frame = pd.DataFrame({"return": benchmark})
    benchmark_frame["turnover"] = 0.0
    benchmark_frame["cost"] = 0.0
    benchmark_frame["equity"] = (1.0 + benchmark).cumprod()
    performance.append(_metric_row("NIFTY50", benchmark_frame))

    base_forecasts = result["walk_forward_forecasts"].copy()
    base_forecasts["date"] = pd.to_datetime(base_forecasts["date"])
    base_forecasts = base_forecasts[
        (base_forecasts["date"] >= start) & (base_forecasts["date"] <= end)
    ]
    base_metrics = base_forecaster_report(base_forecasts, prices)

    for horizon in (1, 5, 20):
        column = f"expected_return_{horizon}d"
        if column not in base_forecasts.columns:
            continue
        bt = _forecast_backtest(base_forecasts, prices, column)
        performance.append(_metric_row(f"base_{horizon}d", bt))

    diagnostics = build_research_diagnostics(
        oos_signals,
        prices,
        ensemble_bt,
        benchmark_returns=benchmark,
        base_forecasts=base_forecasts,
    )

    return {
        "oos_window": {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "observations": int(len(ensemble_bt)),
        },
        "cost_assumptions": {
            "transaction_cost_bps": COST_BPS,
            "slippage_bps": SLIPPAGE_BPS,
        },
        "performance": performance,
        "base_forecaster_predictive_metrics": base_metrics.to_dict("records"),
        "diagnostics": diagnostics,
    }


def main() -> None:
    result = run()
    report = build_research_report(result)
    output_dir = Path("data/research")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "checkpoint1_research_report.json"
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")

    performance = pd.DataFrame(report["performance"])
    csv_path = output_dir / "checkpoint1_performance.csv"
    performance.to_csv(csv_path, index=False)

    print("CHECKPOINT 1 RESEARCH REPORT")
    print(f"OOS window: {report['oos_window']['start']} -> {report['oos_window']['end']}")
    print(performance.to_string(index=False))
    print("\nBase forecaster predictive metrics:")
    print(pd.DataFrame(report["base_forecaster_predictive_metrics"]).to_string(index=False))
    print(f"\nWrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
