"""Exogenous market/macro series aligned to tradable assets by date."""
from __future__ import annotations

import pandas as pd

from market_analyzer.data.yahoo import YahooMarketData


DEFAULT_MACRO = ["^VIX", "^TNX", "DX-Y.NYB", "GC=F", "CL=F"]


class MacroData:
    def __init__(self, symbols: list[str] | None = None):
        self.symbols = symbols or DEFAULT_MACRO

    def fetch(self, start: str, end: str | None = None) -> pd.DataFrame:
        end = end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
        raw = YahooMarketData(start, end, self.symbols).fetch()
        raw["date"] = pd.to_datetime(raw["date"])
        wide = raw.pivot_table(index="date", columns="tic", values="close", aggfunc="last")
        wide.columns = [f"macro_{self._name(c)}" for c in wide.columns]
        return wide.sort_index().reset_index()

    @staticmethod
    def _name(symbol: str) -> str:
        return (
            symbol.replace("^", "")
            .replace("-", "_")
            .replace(".", "_")
            .replace("=", "_")
        ).lower()

    @staticmethod
    def merge_asof(market: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
        left = market.copy()
        left["date"] = pd.to_datetime(left["date"])
        right = macro.copy()
        right["date"] = pd.to_datetime(right["date"])
        right = right.sort_values("date")
        left = left.sort_values("date")
        out = pd.merge_asof(left, right, on="date", direction="backward")
        out["date"] = out["date"].dt.strftime("%Y-%m-%d")
        return out.sort_values(["date", "tic"]).reset_index(drop=True)
