"""Run the repository's mechanical temporal-leakage audit on a synthetic contract fixture.

This script deliberately reports UNKNOWN when a real data source does not carry
an information-availability timestamp. UNKNOWN is preferable to assuming that
same-day information was tradable.
"""
from __future__ import annotations

import argparse
import pandas as pd

from market_analyzer.training.leakage import (
    AuditFinding,
    audit_asof_availability,
    audit_fold_isolation,
    audit_target_end_dates,
    audit_train_target_boundary,
    audit_walk_forward_boundaries,
)
from market_analyzer.training.walk_forward import walk_forward_windows


def build_fixture(start: str, periods: int) -> pd.DataFrame:
    dates = pd.date_range(start, periods=periods, freq="B")
    rows = []
    for tic, base in [("AAA", 100.0), ("BBB", 80.0)]:
        for i, date in enumerate(dates):
            rows.append({"date": date, "tic": tic, "close": base + i, "feature": float(i)})
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--periods", type=int, default=1200)
    parser.add_argument("--horizon", type=int, default=20)
    parser.add_argument("--min-train-days", type=int, default=756)
    parser.add_argument("--test-days", type=int, default=21)
    args = parser.parse_args()

    frame = build_fixture(args.start, args.periods)
    dates = pd.to_datetime(frame["date"])
    windows = list(
        walk_forward_windows(
            dates,
            min_train_days=args.min_train_days,
            test_days=args.test_days,
            horizon_days=args.horizon,
        )
    )

    findings: list[AuditFinding] = [
        audit_target_end_dates(frame, args.horizon),
        audit_train_target_boundary(
            frame,
            windows[0].train_end if windows else dates.iloc[args.min_train_days - 1],
            args.horizon,
        ),
        audit_walk_forward_boundaries(windows, args.horizon),
    ]
    if windows:
        train = frame[dates <= windows[0].train_end]
        test = frame[(dates >= windows[0].test_start) & (dates <= windows[0].test_end)]
        findings.append(audit_fold_isolation(train, test))
    findings.append(
        audit_asof_availability(
            pd.DataFrame({
                "date": pd.to_datetime(["2020-01-02"]),
                "available_at": pd.to_datetime(["2020-01-02"]),
            }),
            "available_at",
        )
    )
    print("=== MECHANICAL LEAKAGE AUDIT ===")
    for finding in findings:
        print(f"{finding.status:7s} {finding.check}: {finding.detail}")
    print(f"windows={len(windows)}")
    print("NOTE: external-source information availability must be audited separately when timestamps are not present.")


if __name__ == "__main__":
    main()
