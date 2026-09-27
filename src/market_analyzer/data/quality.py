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



def classify_jump_context(
    jumps: pd.DataFrame,
    frame: pd.DataFrame,
    actions: pd.DataFrame,
    expected_sessions: pd.DatetimeIndex,
    action_window_days: int = 5,
) -> pd.DataFrame:
    """Attach nearby corporate-action and continuity-gap context to jump candidates.

    This is diagnostic only. It never assigns an adjustment factor or changes prices.
    Exact action matches take precedence over nearby/gap classifications.
    """
    required_jump = ["tic", "date"]
    if any(column not in jumps.columns for column in required_jump):
        raise ValueError("jumps must contain tic and date")
    required_frame = ["tic", "date"]
    if any(column not in frame.columns for column in required_frame):
        raise ValueError("frame must contain tic and date")
    result = jumps.copy()
    result["tic"] = result["tic"].astype("string").str.strip().str.upper()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    market = frame[["tic", "date"]].copy()
    market["tic"] = market["tic"].astype("string").str.strip().str.upper()
    market["date"] = pd.to_datetime(market["date"], errors="coerce")
    market = market.dropna(subset=["tic", "date"])
    sessions = pd.DatetimeIndex(expected_sessions).normalize().sort_values().unique()

    action_rows = actions.copy()
    if action_rows.empty:
        action_rows = pd.DataFrame(columns=["tic", "ex_date", "purpose", "price_factor", "adjustment_type"])
    action_rows["tic"] = action_rows["tic"].astype("string").str.strip().str.upper()
    action_rows["ex_date"] = pd.to_datetime(action_rows["ex_date"], errors="coerce")
    action_rows = action_rows.dropna(subset=["tic", "ex_date"])

    market_dates = {tic: pd.DatetimeIndex(group["date"].unique()).sort_values() for tic, group in market.groupby("tic", sort=False)}
    action_groups = {tic: group.sort_values("ex_date") for tic, group in action_rows.groupby("tic", sort=False)}
    rows = []
    for jump in result.to_dict("records"):
        tic = jump["tic"]
        date = jump["date"]
        row = dict(jump)
        group_actions = action_groups.get(tic, action_rows.iloc[0:0])
        exact = group_actions[group_actions["ex_date"].eq(date)]
        if not exact.empty:
            action = exact.iloc[0]
            row.update({
                "nearest_action_date": action["ex_date"],
                "nearest_action_days": 0,
                "nearest_action_purpose": action.get("purpose"),
                "nearest_action_type": action.get("adjustment_type"),
                "nearest_action_factor": action.get("price_factor"),
                "exact_action": True,
            })
        else:
            row.update({
                "nearest_action_date": pd.NaT,
                "nearest_action_days": pd.NA,
                "nearest_action_purpose": None,
                "nearest_action_type": None,
                "nearest_action_factor": None,
                "exact_action": False,
            })
            if not group_actions.empty:
                distances = (group_actions["ex_date"] - date).abs().dt.days
                nearest_idx = distances.idxmin()
                nearest_days = int(distances.loc[nearest_idx])
                if nearest_days <= action_window_days:
                    action = group_actions.loc[nearest_idx]
                    row.update({
                        "nearest_action_date": action["ex_date"],
                        "nearest_action_days": nearest_days,
                        "nearest_action_purpose": action.get("purpose"),
                        "nearest_action_type": action.get("adjustment_type"),
                        "nearest_action_factor": action.get("price_factor"),
                    })
        observed = market_dates.get(tic, pd.DatetimeIndex([]))
        prior = observed[observed < date]
        previous_observation = prior[-1] if len(prior) else pd.NaT
        gap_sessions = 0
        if pd.notna(previous_observation):
            between = sessions[(sessions > previous_observation) & (sessions < date)]
            gap_sessions = int(len(between))
        row["previous_observation"] = previous_observation
        row["gap_sessions"] = gap_sessions
        row["post_gap"] = gap_sessions > 0
        if row["exact_action"]:
            classification = "exact_action"
        elif row["nearest_action_date"] is not pd.NaT and pd.notna(row["nearest_action_date"]):
            classification = "near_action_and_post_gap" if row["post_gap"] else "near_action"
        elif row["post_gap"]:
            classification = "post_gap"
        else:
            classification = "unexplained"
        row["classification"] = classification
        rows.append(row)
    return pd.DataFrame(rows)
