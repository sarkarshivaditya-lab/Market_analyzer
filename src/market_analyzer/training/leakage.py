"""Mechanical leakage and time-boundary audit helpers.

These checks are intentionally small and deterministic. They validate temporal
contracts; they do not claim that an external source was historically available
unless its own availability timestamp is supplied.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import pandas as pd


@dataclass(frozen=True)
class AuditFinding:
    check: str
    status: str
    detail: str

    def to_dict(self):
        return asdict(self)


def audit_target_end_dates(frame: pd.DataFrame, horizon: int, date_col="date", ticker_col="tic"):
    data = frame.copy()
    data[date_col] = pd.to_datetime(data[date_col])
    ordered = data.sort_values([ticker_col, date_col])
    future = ordered.groupby(ticker_col)[date_col].shift(-horizon)
    valid = future.notna()
    if not valid.any():
        return AuditFinding("target_end_dates", "FAIL", "No observations have a complete forward horizon.")
    return AuditFinding(
        "target_end_dates",
        "PASS",
        f"Checked {int(valid.sum())} observations with complete {horizon}-session forward horizons.",
    )


def audit_train_target_boundary(
    frame: pd.DataFrame,
    train_end,
    horizon: int,
    date_col="date",
    ticker_col="tic",
):
    data = frame.copy()
    data[date_col] = pd.to_datetime(data[date_col])
    train_end = pd.Timestamp(train_end)
    ordered = data.sort_values([ticker_col, date_col])
    future = ordered.groupby(ticker_col)[date_col].shift(-horizon)
    bad = (ordered[date_col] <= train_end) & future.notna() & (future > train_end)
    count = int(bad.sum())
    if count:
        return AuditFinding(
            "train_target_boundary",
            "FAIL",
            f"{count} training-date rows would require target observations after train_end={train_end.date()}.",
        )
    return AuditFinding(
        "train_target_boundary",
        "PASS",
        f"No complete target crosses train_end={train_end.date()} for horizon={horizon}.",
    )


def audit_walk_forward_boundaries(windows, horizon: int):
    failures = []
    previous_test_end = None
    for i, window in enumerate(windows):
        if window.train_end >= window.test_start:
            failures.append(f"window {i}: train_end >= test_start")
        if (window.test_start - window.train_end).days < horizon:
            failures.append(f"window {i}: purge shorter than {horizon} calendar days")
        if previous_test_end is not None and window.test_start <= previous_test_end:
            failures.append(f"window {i}: test periods overlap or move backward")
        previous_test_end = window.test_end
    if failures:
        return AuditFinding("walk_forward_boundaries", "FAIL", "; ".join(failures))
    return AuditFinding(
        "walk_forward_boundaries",
        "PASS",
        f"Validated {len(windows)} chronological windows with a >= {horizon}-day calendar purge.",
    )


def audit_asof_availability(
    frame: pd.DataFrame,
    availability_col: str,
    decision_col: str = "date",
):
    if availability_col not in frame.columns:
        return AuditFinding(
            "asof_availability",
            "UNKNOWN",
            f"Column {availability_col!r} is absent; historical information availability cannot be mechanically proven.",
        )
    available = pd.to_datetime(frame[availability_col], errors="coerce")
    decision = pd.to_datetime(frame[decision_col], errors="coerce")
    bad = available.notna() & decision.notna() & (available > decision)
    if bad.any():
        return AuditFinding(
            "asof_availability",
            "FAIL",
            f"{int(bad.sum())} rows have information availability after the decision date.",
        )
    return AuditFinding(
        "asof_availability",
        "PASS",
        "All supplied availability timestamps are on or before the decision date.",
    )


def audit_point_in_time_membership(
    frame: pd.DataFrame,
    universe_by_date: dict[pd.Timestamp, set[str]],
    date_col="date",
    ticker_col="tic",
):
    data = frame.copy()
    data[date_col] = pd.to_datetime(data[date_col]).dt.normalize()
    bad = 0
    checked = 0
    for row in data[[date_col, ticker_col]].itertuples(index=False):
        dt = row[0]
        candidates = [d for d in universe_by_date if d <= dt]
        if not candidates:
            continue
        asof = max(candidates)
        checked += 1
        if row[1] not in universe_by_date[asof]:
            bad += 1
    if bad:
        return AuditFinding(
            "point_in_time_membership",
            "FAIL",
            f"{bad} of {checked} checked rows are outside the supplied as-of universe.",
        )
    return AuditFinding(
        "point_in_time_membership",
        "PASS",
        f"All {checked} checked rows are members of the supplied point-in-time universe.",
    )


def audit_fold_isolation(train, test, date_col="date"):
    train_dates = pd.to_datetime(train[date_col])
    test_dates = pd.to_datetime(test[date_col])
    if train_dates.max() >= test_dates.min():
        return AuditFinding(
            "fold_isolation",
            "FAIL",
            "Training data reaches or exceeds the first test date.",
        )
    return AuditFinding(
        "fold_isolation",
        "PASS",
        f"train_max={train_dates.max().date()} < test_min={test_dates.min().date()}",
    )


def audit_feature_availability_columns(frame: pd.DataFrame, required_timestamp_pairs: dict[str, str]):
    findings = []
    for feature, availability in required_timestamp_pairs.items():
        if feature not in frame.columns:
            findings.append(AuditFinding(feature, "UNKNOWN", f"Feature {feature!r} is absent."))
            continue
        if availability not in frame.columns:
            findings.append(AuditFinding(
                feature,
                "UNKNOWN",
                f"No availability timestamp {availability!r}; causal availability cannot be proven.",
            ))
            continue
        finding = audit_asof_availability(frame, availability)
        findings.append(AuditFinding(feature, finding.status, finding.detail))
    return findings
