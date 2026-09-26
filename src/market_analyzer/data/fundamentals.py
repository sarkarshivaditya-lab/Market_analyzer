from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class FundamentalSnapshot:
    ticker: str
    effective_at: pd.Timestamp
    filed_at: pd.Timestamp
    source: str
    values: dict[str, float]


class FundamentalProvider(Protocol):
    def fetch(self, tickers: list[str], as_of: pd.Timestamp) -> list[FundamentalSnapshot]:
        ...


class CsvFundamentalProvider:
    """Historical provider for point-in-time snapshots.

    CSV columns: ticker,effective_at,filed_at,source,<metric columns>.
    A row is usable only when filed_at <= as_of.
    """

    def __init__(self, path: str):
        self.path = path

    def fetch(self, tickers: list[str], as_of: pd.Timestamp) -> list[FundamentalSnapshot]:
        frame = pd.read_csv(self.path)
        required = {"ticker", "effective_at", "filed_at", "source"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Missing fundamental columns: {sorted(missing)}")
        frame["effective_at"] = pd.to_datetime(frame["effective_at"], utc=True)
        frame["filed_at"] = pd.to_datetime(frame["filed_at"], utc=True)
        cutoff = pd.Timestamp(as_of, tz="UTC") if pd.Timestamp(as_of).tzinfo is None else pd.Timestamp(as_of).tz_convert("UTC")
        frame = frame[(frame["ticker"].isin(tickers)) & (frame["filed_at"] <= cutoff)]
        out = []
        metrics = [c for c in frame.columns if c not in required]
        for _, row in frame.sort_values("filed_at").iterrows():
            values = {c: float(row[c]) for c in metrics if pd.notna(row[c])}
            out.append(FundamentalSnapshot(
                str(row["ticker"]), row["effective_at"], row["filed_at"], str(row["source"]), values
            ))
        return out


def merge_fundamentals_asof(market: pd.DataFrame, snapshots: list[FundamentalSnapshot]) -> pd.DataFrame:
    if not snapshots:
        return market.copy()
    rows = []
    for s in snapshots:
        row = {"tic": s.ticker, "effective_at": s.effective_at, "filed_at": s.filed_at}
        row.update({f"fund_{k}": v for k, v in s.values.items()})
        rows.append(row)
    snap = pd.DataFrame(rows).sort_values(["tic", "filed_at"])
    left = market.copy()
    left["_asof"] = pd.to_datetime(left["date"], utc=True)
    snap["_asof"] = snap["filed_at"]
    metric_cols = [c for c in snap.columns if c.startswith("fund_")]
    out = pd.merge_asof(
        left.sort_values(["tic", "_asof"]),
        snap[["tic", "_asof", *metric_cols]].sort_values(["tic", "_asof"]),
        by="tic", on="_asof", direction="backward",
    )
    return out.drop(columns="_asof").sort_values(["date", "tic"]).reset_index(drop=True)
