"""Small end-to-end research pipeline."""
from __future__ import annotations

from market_analyzer.data.yahoo import YahooMarketData
from market_analyzer.features.engineering import FeatureEngineer
from market_analyzer.models.anomaly import compute_market_anomaly_score
from market_analyzer.reporting import latest_market_snapshot


def run(start_date: str, end_date: str, tickers: list[str]):
    loader = YahooMarketData(start_date, end_date, tickers)
    raw = loader.fetch()
    engineered = FeatureEngineer(include_vix=False, include_turbulence=len(tickers) > 1).transform(raw)
    scored = compute_market_anomaly_score(engineered)
    return latest_market_snapshot(scored)


if __name__ == "__main__":
    result = run(
        start_date="2015-01-01",
        end_date="2026-01-01",
        tickers=["SPY", "QQQ", "GLD", "TLT"],
    )
    print(result.to_string(index=False))
