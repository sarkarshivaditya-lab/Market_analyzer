"""Audit a previously populated local NSE SQLite store."""
from __future__ import annotations

import argparse
import pandas as pd

from market_analyzer.data.local import NSELocalMarketStore
from market_analyzer.data.quality import audit_market_data, price_jump_details, ticker_gap_details


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="data/market/nse.sqlite")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    store = NSELocalMarketStore(args.store)
    frame = store.load(args.start, args.end, args.tickers)
    report = audit_market_data(frame)
    print("=== MARKET QUALITY SUMMARY ===")
    print(f"valid={report.valid}")
    print(f"rows={report.rows} tickers={report.tickers}")
    print(f"date_range={report.first_date} -> {report.last_date}")
    print(
        "duplicates={0} missing_values={1} invalid_ohlc={2} nonpositive_prices={3} "
        "negative_volume={4} zero_volume={5} price_jump_candidates={6}".format(
            report.duplicate_rows,
            report.missing_values,
            report.invalid_ohlc_rows,
            report.nonpositive_price_rows,
            report.negative_volume_rows,
            report.zero_volume_rows,
            report.price_jump_candidates,
        )
    )

    jumps = price_jump_details(frame).head(max(args.top, 0))
    print()
    print(f"=== TOP PRICE-JUMP CANDIDATES ({len(jumps)}) ===")
    print(jumps.to_string(index=False) if not jumps.empty else "None.")

    sessions = pd.DatetimeIndex(frame["date"].unique()).sort_values() if not frame.empty else pd.DatetimeIndex([])
    gaps = ticker_gap_details(frame, sessions)
    print()
    print(f"=== TICKER SESSION GAPS ({len(gaps)}) ===")
    if gaps.empty:
        print("None.")
    else:
        print(gaps.sort_values("missing_sessions", ascending=False).head(max(args.top, 0)).to_string(index=False))

    print()
    coverage = store.coverage(args.tickers)
    print("=== COVERAGE ===")
    print(coverage.to_string(index=False) if not coverage.empty else "No stored coverage.")


if __name__ == "__main__":
    main()
