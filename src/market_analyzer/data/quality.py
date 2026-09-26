"""Data-quality checks for normalized market history."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import pandas as pd


@dataclass(frozen=True)
class MarketQualityReport:
    rows: int
    tickers: int
    first_date: str | None
    last_date: str | None
    duplicate_rows: int
    missing_values: int
    invalid_ohlc_rows: int
    nonpositive_price_rows: int
    negative_volume_rows: int
    zero_volume_rows: int
    price_jump_candidates: int
    ticker_date_gaps: int

    @property
    def valid(self) -> bool:
        return (
            self.duplicate_rows == 0
            and self.missing_values == 0
            and self.invalid_ohlc_rows == 0
            and self.nonpositive_price_rows == 0
            and self.negative_volume_rows == 0
        )

    def to_dict(self) -> dict:
        return asdict(self)


def audit_market_data(frame: pd.DataFrame, expected_sessions: pd.DatetimeIndex | None = None) -> MarketQualityReport:
    required = ["date", "open", "high", "low", "close", "volume", "tic"]
    missing_columns = [column for column in required if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Missing market columns: {missing_columns}")

    data = frame[required].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    for column in ["open", "high", "low", "close", "volume"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data["tic"] = data["tic"].astype("string").str.strip().str.upper()

    missing_values = int(data.isna().any(axis=1).sum())
    duplicate_rows = int(data.duplicated(["date", "tic"], keep=False).sum())

    complete = data.dropna(subset=required)
    invalid_ohlc = (
        (complete["high"] < complete[["open", "close"]].max(axis=1))
        | (complete["low"] > complete[["open", "close"]].min(axis=1))
        | (complete["high"] < complete["low"])
    )
    invalid_ohlc_rows = int(invalid_ohlc.sum())

    nonpositive = (complete[["open", "high", "low", "close"]] <= 0).any(axis=1)
    nonpositive_price_rows = int(nonpositive.sum())
    negative_volume_rows = int((complete["volume"] < 0).sum())
    zero_volume_rows = int((complete["volume"] == 0).sum())

    ordered = complete.sort_values(["tic", "date"]).copy()
    previous_close = ordered.groupby("tic")["close"].shift(1)
    ratio = ordered["close"] / previous_close
    price_jump_candidates = int(((ratio >= 1.5) | (ratio <= (1 / 1.5))).fillna(False).sum())

    ticker_date_gaps = 0
    if expected_sessions is not None and len(expected_sessions):
        sessions = pd.DatetimeIndex(expected_sessions).normalize().sort_values().unique()
        for _, group in complete.groupby("tic", sort=False):
            observed = pd.DatetimeIndex(group["date"].dt.normalize().unique())
            ticker_date_gaps += int(len(sessions.difference(observed)))

    first_date = None if complete.empty else complete["date"].min().strftime("%Y-%m-%d")
    last_date = None if complete.empty else complete["date"].max().strftime("%Y-%m-%d")
    return MarketQualityReport(
        rows=len(data),
        tickers=int(data["tic"].nunique(dropna=True)),
        first_date=first_date,
        last_date=last_date,
        duplicate_rows=duplicate_rows,
        missing_values=missing_values,
        invalid_ohlc_rows=invalid_ohlc_rows,
        nonpositive_price_rows=nonpositive_price_rows,
        negative_volume_rows=negative_volume_rows,
        zero_volume_rows=zero_volume_rows,
        price_jump_candidates=price_jump_candidates,
        ticker_date_gaps=ticker_date_gaps,
    )
