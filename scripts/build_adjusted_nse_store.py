#!/usr/bin/env python3
"""Build a separate corporate-action-adjusted NSE research SQLite store."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from market_analyzer.data.corporate_actions import build_adjusted_research_frame, parse_corporate_actions
from market_analyzer.data.local import NSELocalMarketStore


def _actions_in_window(actions: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    result = actions.copy()
    result["ex_date"] = pd.to_datetime(result["ex_date"], errors="coerce")
    start_date = pd.Timestamp(start)
    end_date = pd.Timestamp(end)
    return result[result["ex_date"].between(start_date, end_date)].copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-store", default="data/market/nse.sqlite")
    parser.add_argument("--adjusted-store", default="data/market/nse_adjusted.sqlite")
    parser.add_argument("--actions", default="data/raw/nse/corporate_actions_api.csv")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2026-09-27")
    args = parser.parse_args()

    raw = NSELocalMarketStore(args.raw_store)
    frame = raw.load(args.start, args.end)
    if frame.empty:
        raise ValueError("Raw NSE store returned no rows for the requested window.")

    actions_frame = pd.read_csv(args.actions)
    actions = parse_corporate_actions(actions_frame)
    actions = _actions_in_window(actions, args.start, args.end)
    adjustable = actions.dropna(subset=["ex_date", "price_factor"]).copy()
    adjusted = build_adjusted_research_frame(frame, adjustable)

    output = NSELocalMarketStore(args.adjusted_store)
    inserted = output.upsert(adjusted.drop(columns=["price_adjusted"]))
    coverage = output.coverage()

    print(f"raw_rows={len(frame)}")
    print(f"parsed_actions={len(actions)}")
    print(f"adjustable_actions={len(adjustable)}")
    print(f"adjusted_rows_written={inserted}")
    print(f"adjusted_store={Path(args.adjusted_store)}")
    print(f"adjusted_tickers={len(coverage)}")
    print(f"raw_store_unchanged={Path(args.raw_store).resolve() != Path(args.adjusted_store).resolve()}")


if __name__ == "__main__":
    main()
