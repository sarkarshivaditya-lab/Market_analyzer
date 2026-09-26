#!/usr/bin/env python3
"""Build an auditable NSE universe registry from the durable local store."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from market_analyzer.data.local import NSELocalMarketStore
from market_analyzer.data.universe import UniverseConfig, build_universe_registry

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="data/market/nse.sqlite")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2026-09-27")
    parser.add_argument("--output", default="data/market/nse_universe.csv")
    parser.add_argument("--min-history-sessions", type=int, default=756)
    parser.add_argument("--min-coverage-ratio", type=float, default=0.70)
    parser.add_argument("--min-median-turnover", type=float, default=10_000_000.0)
    args = parser.parse_args()

    store = NSELocalMarketStore(args.store)
    frame = store.load(args.start, args.end)
    sessions = pd.DatetimeIndex(frame["date"].unique()).sort_values()
    config = UniverseConfig(
        min_history_sessions=args.min_history_sessions,
        min_coverage_ratio=args.min_coverage_ratio,
        min_median_turnover=args.min_median_turnover,
    )
    registry = build_universe_registry(frame, sessions, config)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    registry.to_csv(output, index=False)
    eligible = registry[registry["eligible"]]
    print(f"symbols={len(registry)} eligible={len(eligible)} output={output}")
    print(eligible[["tic", "first_date", "last_date", "observations", "coverage_ratio", "median_turnover"]].to_string(index=False))

if __name__ == "__main__":
    main()
