"""Corporate-action parsing and conservative historical price adjustment."""
from __future__ import annotations

from dataclasses import dataclass
import re
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CorporateAction:
    tic: str
    ex_date: pd.Timestamp
    purpose: str
    price_factor: float | None
    adjustment_type: str


def _ratio(text: str) -> tuple[float, float] | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def parse_corporate_action(symbol: str, ex_date: str, purpose: str) -> CorporateAction:
    purpose_upper = str(purpose).upper().strip()
    tic = str(symbol).strip().upper()
    date = pd.Timestamp(ex_date)

    # Composite NSE descriptions can mention both a bonus and a face-value
    # split. In this dataset the historical price series already reflects the
    # face-value subdivision, while the observed discontinuity corresponds to
    # the bonus factor. Treat the composite event as the bonus adjustment.
    if "BONUS" in purpose_upper and (
        "SPLIT" in purpose_upper or "SPLT" in purpose_upper
        or "SUB-DIVISION" in purpose_upper or "SUBDIVISION" in purpose_upper
    ):
        ratio = _ratio(purpose_upper)
        if ratio:
            bonus, existing = ratio
            return CorporateAction(tic, date, purpose, existing / (existing + bonus), "bonus")

    if "SPLIT" in purpose_upper or "SPLT" in purpose_upper or "SUB-DIVISION" in purpose_upper or "SUBDIVISION" in purpose_upper:
        values = re.findall(r"(?:RS\.?\s*)?(\d+(?:\.\d+)?)", purpose_upper)
        if len(values) >= 2:
            old_value, new_value = float(values[-2]), float(values[-1])
            if old_value > 0 and new_value > 0 and re.search(
                r"FACE VALUE|PER SHARE|FROM .* TO|FV\s+SPLT|FV\.\s*SPLT", purpose_upper
            ):
                return CorporateAction(tic, date, purpose, new_value / old_value, "split")
        return CorporateAction(tic, date, purpose, None, "review")

    # NCRPS/CRPS are preference shares issued under a scheme, not additional
    # equity shares, so they must not be used to back-adjust the equity series.
    if re.search(r"\b(?:N?CRPS|PREFERENCE)\b", purpose_upper):
        return CorporateAction(tic, date, purpose, None, "review")

    if "BONUS" in purpose_upper:
        ratio = _ratio(purpose_upper)
        if ratio:
            bonus, existing = ratio
            return CorporateAction(tic, date, purpose, existing / (existing + bonus), "bonus")
        return CorporateAction(tic, date, purpose, None, "review")

    return CorporateAction(tic, date, purpose, None, "review")


def parse_corporate_actions(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["symbol", "ex_date", "purpose"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing corporate-action columns: {missing}")
    rows = []
    for row in frame[required].itertuples(index=False):
        try:
            action = parse_corporate_action(row.symbol, row.ex_date, row.purpose)
            rows.append({
                "tic": action.tic,
                "ex_date": action.ex_date,
                "purpose": action.purpose,
                "price_factor": action.price_factor,
                "adjustment_type": action.adjustment_type,
            })
        except (TypeError, ValueError):
            rows.append({
                "tic": str(row.symbol).strip().upper(),
                "ex_date": pd.NaT,
                "purpose": str(row.purpose),
                "price_factor": None,
                "adjustment_type": "review",
            })
    return pd.DataFrame(rows)


def apply_backward_adjustments(frame: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "tic", "open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing market columns: {missing}")
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result["tic"] = result["tic"].astype(str).str.strip().str.upper()
    if actions.empty:
        return result.sort_values(["tic", "date"]).reset_index(drop=True)
    usable = actions.dropna(subset=["ex_date", "price_factor"]).copy()
    usable["ex_date"] = pd.to_datetime(usable["ex_date"], errors="coerce")
    usable["price_factor"] = pd.to_numeric(usable["price_factor"], errors="coerce")
    usable = usable.dropna(subset=["ex_date", "price_factor"])
    usable = usable[usable["price_factor"] > 0]
    if usable.empty:
        return result.sort_values(["tic", "date"]).reset_index(drop=True)
    # Build one cumulative factor per ticker/date instead of scanning the full
    # market frame once per corporate action. This is important for the ~5M-row
    # NSE store and preserves the invariant that raw SQLite is never mutated.
    for tic, action_group in usable.groupby("tic", sort=False):
        mask = result["tic"].eq(tic)
        if not mask.any():
            continue
        dates = result.loc[mask, "date"].to_numpy(dtype="datetime64[ns]")
        actions_sorted = action_group.sort_values("ex_date")
        ex_dates = actions_sorted["ex_date"].to_numpy(dtype="datetime64[ns]")
        factors = actions_sorted["price_factor"].to_numpy(dtype=float)
        cumulative = factors[::-1].cumprod()[::-1]
        positions = ex_dates.searchsorted(dates, side="right")
        # For a date before the first ex-date, every action contributes. For a
        # date on/after the latest ex-date, no historical adjustment remains.
        adjustment = np.ones(len(dates), dtype=float)
        before = positions < len(cumulative)
        adjustment[before] = cumulative[positions[before]]
        idx = result.index[mask]
        for column in ["open", "high", "low", "close"]:
            result.loc[idx, column] = result.loc[idx, column].to_numpy(dtype=float) * adjustment
        result.loc[idx, "volume"] = result.loc[idx, "volume"].to_numpy(dtype=float) / adjustment
    return result.sort_values(["tic", "date"]).reset_index(drop=True)


def build_adjusted_research_frame(frame: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    """Return a corporate-action-adjusted research copy without mutating raw data."""
    result = apply_backward_adjustments(frame, actions)
    result["price_adjusted"] = True
    return result
