"""Point-in-time universe selection for the local NSE cash-market store."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
import pandas as pd

REQUIRED = ["date", "open", "high", "low", "close", "volume", "tic"]
NON_EQUITY_PATTERNS = (
    r"(^|_)(NIFTY|SENSEX)(_|$)",
    r"(ETF|BEES)$",
    r"^(SETF|MON100|GOLDBEES|SILVERBEES|LIQUIDBEES|BANKBEES|ITBEES|PHARMABEES)",
    r"(GILT|LIQUID|GOLD|SILVER)(ETF|BEES)?$",
)

@dataclass(frozen=True)
class UniverseConfig:
    min_history_sessions: int = 756
    min_coverage_ratio: float = 0.70
    min_median_turnover: float = 10_000_000.0
    max_stale_sessions: int = 20

@dataclass(frozen=True)
class UniverseRow:
    tic: str
    first_date: str
    last_date: str
    observations: int
    coverage_ratio: float
    median_volume: float
    median_turnover: float
    instrument_class: str
    eligible: bool
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)

def _validate(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        raise ValueError(f"Missing market columns: {missing}")
    data = frame[REQUIRED].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    data["tic"] = data["tic"].astype("string").str.strip().str.upper()
    for col in ["open", "high", "low", "close", "volume"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=REQUIRED).drop_duplicates(["date", "tic"])
    return data.sort_values(["tic", "date"]).reset_index(drop=True)

def _looks_like_non_equity(tic: str) -> bool:
    return any(re.search(pattern, tic, flags=re.IGNORECASE) for pattern in NON_EQUITY_PATTERNS)

def _sessions_between(sessions: pd.DatetimeIndex, first: pd.Timestamp, last: pd.Timestamp) -> int:
    return int(((sessions >= first) & (sessions <= last)).sum())

def _metrics(data: pd.DataFrame, sessions: pd.DatetimeIndex) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=[
            "tic", "first_date", "last_date", "observations",
            "coverage_ratio", "median_volume", "median_turnover",
        ])
    work = data.copy()
    work["turnover"] = work["close"] * work["volume"]
    rows = []
    for tic, group in work.groupby("tic", sort=True):
        first = group["date"].min()
        last = group["date"].max()
        expected = _sessions_between(sessions, first, last)
        rows.append({
            "tic": tic,
            "first_date": first,
            "last_date": last,
            "observations": int(len(group)),
            "coverage_ratio": float(len(group) / expected) if expected else 0.0,
            "median_volume": float(group["volume"].median()),
            "median_turnover": float(group["turnover"].median()),
        })
    return pd.DataFrame(rows)

def build_universe_registry(frame: pd.DataFrame, expected_sessions: pd.DatetimeIndex | None = None, config: UniverseConfig | None = None) -> pd.DataFrame:
    config = config or UniverseConfig()
    data = _validate(frame)
    sessions = (
        pd.DatetimeIndex(expected_sessions).normalize().unique().sort_values()
        if expected_sessions is not None and len(expected_sessions)
        else pd.DatetimeIndex(data["date"].unique()).sort_values()
    )
    metrics = _metrics(data, sessions)
    if metrics.empty:
        return metrics.assign(
            instrument_class=pd.Series(dtype=str),
            eligible=pd.Series(dtype=bool),
            reason=pd.Series(dtype=str),
        )
    rows = []
    for row in metrics.itertuples(index=False):
        reasons = []
        instrument_class = "nse_eq_series"
        if _looks_like_non_equity(row.tic):
            instrument_class = "screened_non_equity"
            reasons.append("symbol_screen")
        if row.observations < config.min_history_sessions:
            reasons.append("insufficient_history")
        if row.coverage_ratio < config.min_coverage_ratio:
            reasons.append("insufficient_coverage")
        if row.median_turnover < config.min_median_turnover:
            reasons.append("insufficient_liquidity")
        rows.append(UniverseRow(
            tic=row.tic,
            first_date=pd.Timestamp(row.first_date).strftime("%Y-%m-%d"),
            last_date=pd.Timestamp(row.last_date).strftime("%Y-%m-%d"),
            observations=int(row.observations),
            coverage_ratio=float(row.coverage_ratio),
            median_volume=float(row.median_volume),
            median_turnover=float(row.median_turnover),
            instrument_class=instrument_class,
            eligible=not reasons,
            reason="eligible" if not reasons else ",".join(reasons),
        ).to_dict())
    return pd.DataFrame(rows).sort_values(["eligible", "tic"], ascending=[False, True]).reset_index(drop=True)

def eligible_tickers_on(frame: pd.DataFrame, as_of: str | pd.Timestamp, expected_sessions: pd.DatetimeIndex | None = None, config: UniverseConfig | None = None) -> list[str]:
    """Build a training universe using no observations after as_of."""
    config = config or UniverseConfig()
    as_of_ts = pd.Timestamp(as_of).normalize()
    data = _validate(frame)
    data = data[data["date"] <= as_of_ts].copy()
    if data.empty:
        return []
    sessions = (
        pd.DatetimeIndex(expected_sessions).normalize().unique().sort_values()
        if expected_sessions is not None and len(expected_sessions)
        else pd.DatetimeIndex(data["date"].unique()).sort_values()
    )
    sessions = sessions[sessions <= as_of_ts]
    metrics = _metrics(data, sessions)
    eligible = metrics[
        (metrics["observations"] >= config.min_history_sessions)
        & (metrics["coverage_ratio"] >= config.min_coverage_ratio)
        & (metrics["median_turnover"] >= config.min_median_turnover)
        & ~metrics["tic"].map(_looks_like_non_equity)
    ]
    return eligible["tic"].tolist()
