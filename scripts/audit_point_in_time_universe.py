#!/usr/bin/env python3
"""Audit point-in-time NSE universe coverage, gaps, and large price moves."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from market_analyzer.data.local import NSELocalMarketStore
from market_analyzer.data.quality import price_jump_details, ticker_gap_details
from market_analyzer.data.universe import UniverseConfig, eligible_tickers_on


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="data/market/nse_adjusted.sqlite")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2026-09-27")
    parser.add_argument("--universe", default="data/market/nse_universe.csv")
    parser.add_argument("--min-history-sessions", type=int, default=756)
    parser.add_argument("--min-coverage-ratio", type=float, default=0.70)
    parser.add_argument("--min-median-turnover", type=float, default=10_000_000.0)
    parser.add_argument("--jump-threshold", type=float, default=1.5)
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--output", default="data/market/point_in_time_universe_audit.csv")
    args = parser.parse_args()

    store = NSELocalMarketStore(args.store)
    frame = store.load(args.start, args.end)
    if frame.empty:
        raise SystemExit("No market data loaded.")

    sessions = pd.DatetimeIndex(frame["date"].unique()).sort_values()
    config = UniverseConfig(
        min_history_sessions=args.min_history_sessions,
        min_coverage_ratio=args.min_coverage_ratio,
        min_median_turnover=args.min_median_turnover,
    )

    registry = pd.read_csv(args.universe) if Path(args.universe).exists() else pd.DataFrame()
    eligible_full_period = set(
        registry.loc[registry["eligible"].astype(bool), "tic"].astype(str).str.upper()
    ) if {"tic", "eligible"}.issubset(registry.columns) else set()

    print("=== POINT-IN-TIME UNIVERSE AUDIT ===")
    print(f"store={args.store}")
    print(f"date_range={sessions.min().date()} -> {sessions.max().date()}")
    print(f"full_period_eligible={len(eligible_full_period)}")

    periods = pd.date_range(sessions.min(), sessions.max(), freq="QS")
    rows = []
    for as_of in periods:
        tickers = eligible_tickers_on(frame, as_of, sessions, config)
        rows.append({
            "as_of": as_of.strftime("%Y-%m-%d"),
            "eligible_tickers": len(tickers),
        })
    snapshot = pd.DataFrame(rows)
    print("=== QUARTERLY ELIGIBLE COUNTS ===")
    print(snapshot.to_string(index=False))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot.to_csv(output, index=False)

    eligible_frame = frame[
        frame["tic"].astype(str).str.upper().isin(eligible_full_period)
    ].copy()
    gaps = ticker_gap_details(eligible_frame, sessions)
    if not gaps.empty:
        gap_stats = gaps["missing_sessions"].describe(percentiles=[0.5, 0.9, 0.95]).round(2)
        print()
        print("=== FULL-PERIOD ELIGIBLE GAP SUMMARY ===")
        print(f"tickers_with_gaps={len(gaps)}")
        print(f"total_missing_sessions={int(gaps['missing_sessions'].sum())}")
        print(f"median_missing_sessions={gap_stats.get('50%', 0)}")
        print(f"p90_missing_sessions={gap_stats.get('90%', 0)}")
        print(f"p95_missing_sessions={gap_stats.get('95%', 0)}")
        print("top_gap_tickers=")
        print(gaps.sort_values("missing_sessions", ascending=False).head(args.top).to_string(index=False))
    else:
        print()
        print("=== FULL-PERIOD ELIGIBLE GAP SUMMARY ===")
        print("tickers_with_gaps=0")

    jumps = price_jump_details(eligible_frame, threshold=args.jump_threshold)
    print()
    print("=== FULL-PERIOD ELIGIBLE PRICE-JUMP SUMMARY ===")
    print(f"jump_candidates={len(jumps)}")
    if not jumps.empty:
        print(jumps.head(args.top).to_string(index=False))

    print()
    print(f"audit_output={output}")


if __name__ == "__main__":
    main()
