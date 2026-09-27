import pandas as pd

from market_analyzer.training.leakage import (
    audit_asof_availability,
    audit_fold_isolation,
    audit_target_end_dates,
    audit_train_target_boundary,
    audit_walk_forward_boundaries,
)
from market_analyzer.training.walk_forward import WalkForwardWindow


def fixture():
    dates = pd.date_range("2020-01-01", periods=30, freq="B")
    return pd.DataFrame({
        "date": dates.tolist() * 1,
        "tic": ["AAA"] * len(dates),
        "close": range(len(dates)),
    })


def test_target_end_dates_reports_complete_horizon():
    finding = audit_target_end_dates(fixture(), horizon=5)
    assert finding.status == "PASS"


def test_train_target_boundary_detects_crossing_target():
    frame = fixture()
    train = frame.iloc[:6].copy()\n    finding = audit_train_target_boundary(frame, train, frame["date"].iloc[5], horizon=5)
    assert finding.status == "FAIL"


def test_train_target_boundary_passes_after_purge():
    frame = fixture()
    train = frame.iloc[:1].copy()\n    finding = audit_train_target_boundary(frame, train, frame["date"].iloc[0], horizon=5)
    assert finding.status == "PASS"


def test_walk_forward_boundaries_reject_overlap():
    windows = [
        WalkForwardWindow(
            pd.Timestamp("2020-01-01"),
            pd.Timestamp("2020-01-10"),
            pd.Timestamp("2020-01-15"),
            pd.Timestamp("2020-01-20"),
        ),
        WalkForwardWindow(
            pd.Timestamp("2020-01-01"),
            pd.Timestamp("2020-01-18"),
            pd.Timestamp("2020-01-20"),
            pd.Timestamp("2020-01-25"),
        ),
    ]
    finding = audit_walk_forward_boundaries(windows, horizon=5)
    assert finding.status == "FAIL"


def test_fold_isolation():
    frame = fixture()
    finding = audit_fold_isolation(frame.iloc[:15], frame.iloc[15:])
    assert finding.status == "PASS"


def test_asof_availability():
    frame = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-02", "2020-01-03"]),
        "available_at": pd.to_datetime(["2020-01-02", "2020-01-04"]),
    })
    finding = audit_asof_availability(frame, "available_at")
    assert finding.status == "FAIL"
