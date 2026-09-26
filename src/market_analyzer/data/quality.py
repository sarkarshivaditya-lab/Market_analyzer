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


def price_jump_details(frame: pd.DataFrame, threshold: float = 1.5) -> pd.DataFrame:
    required = ["date", "tic", "close"]
    missing_columns = [column for column in required if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Missing market columns: {missing_columns}")
    data = frame[required].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    data["tic"] = data["tic"].astype("string").str.strip().str.upper()
    data = data.dropna(subset=required).sort_values(["tic", "date"]).copy()
    data["previous_close"] = data.groupby("tic")["close"].shift(1)
    data["jump_ratio"] = data["close"] / data["previous_close"]
    candidates = data[(data["jump_ratio"] >= threshold) | (data["jump_ratio"] <= (1 / threshold))].copy()
    candidates["jump_pct"] = (candidates["jump_ratio"] - 1.0) * 100.0
    return candidates[["tic", "date", "previous_close", "close", "jump_pct"]].sort_values(
        "jump_pct", key=lambda values: values.abs(), ascending=False
    ).reset_index(drop=True)


def ticker_gap_details(frame: pd.DataFrame, expected_sessions: pd.DatetimeIndex | None) -> pd.DataFrame:
    required = ["date", "tic"]
    missing_columns = [column for column in required if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Missing market columns: {missing_columns}")
    if expected_sessions is None or len(expected_sessions) == 0:
        return pd.DataFrame(columns=["tic", "missing_sessions"])
    data = frame[required].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["tic"] = data["tic"].astype("string").str.strip().str.upper()
    data = data.dropna(subset=required)
    sessions = pd.DatetimeIndex(expected_sessions).normalize().sort_values().unique()
    rows = []
    for tic, group in data.groupby("tic", sort=True):
        observed = pd.DatetimeIndex(group["date"].dt.normalize().unique())
        if len(observed):
            expected = sessions[(sessions >= observed.min()) & (sessions <= observed.max())]
            missing = expected.difference(observed)
            if len(missing):
                rows.append({"tic": tic, "missing_sessions": int(len(missing))})
    return pd.DataFrame(rows, columns=["tic", "missing_sessions"])


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

    price_jump_candidates = len(price_jump_details(complete))

    ticker_date_gaps = 0
    if expected_sessions is not None and len(expected_sessions):
        sessions = pd.DatetimeIndex(expected_sessions).normalize().sort_values().unique()
        for _, group in complete.groupby("tic", sort=False):
            observed = pd.DatetimeIndex(group["date"].dt.normalize().unique())
            if len(observed):
                expected = sessions[(sessions >= observed.min()) & (sessions <= observed.max())]
                ticker_date_gaps += int(len(expected.difference(observed)))

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
