"""Tradable market-data layer.

Keeps tradable OHLCV data separate from exogenous macro series so feature
construction cannot accidentally treat VIX/rates as investable assets.
"""
from __future__ import annotations

import pandas as pd

from market_analyzer.data.yahoo import YahooMarketData


class MarketData:
    def __init__(self, tickers: list[str]):
        if not tickers:
            raise ValueError("tickers must not be empty")
        self.tickers = tickers

    def fetch(self, start: str, end: str | None = None, auto_adjust: bool = True) -> pd.DataFrame:
        end = end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
        return YahooMarketData(start, end, self.tickers).fetch(auto_adjust=auto_adjust)

    @staticmethod
    def validate(frame: pd.DataFrame) -> None:
        required = {"date", "tic", "open", "high", "low", "close", "volume"}
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"Missing market columns: {sorted(missing)}")
        if frame["tic"].isin(["^VIX"]).any():
            raise ValueError("Exogenous instruments such as ^VIX must not be in tradable market data.")
