"""Populate and inspect the durable NSE local market store.

Examples:
    PYTHONPATH=src python scripts/build_nse_store.py --start 2015-01-01 --end 2026-01-01
    PYTHONPATH=src python scripts/build_nse_store.py --start 2024-01-01 --end 2026-01-01 --tickers RELIANCE TCS INFY
"""
from __future__ import annotations

import argparse

from market_analyzer.data.local import NSELocalMarketData


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--store", default="data/market/nse.sqlite")
    parser.add_argument("--cache", default="data/raw/nse")
    parser.add_argument("--tickers", nargs="*", default=None)
    args = parser.parse_args()

    provider = NSELocalMarketData(
        args.start,
        args.end,
        tickers=args.tickers,
        store_path=args.store,
        cache_dir=args.cache,
    )
    frame = provider.fetch()
    coverage = provider.store.coverage(args.tickers)
    print(f"stored rows returned: {len(frame):,}")
    print(f"tickers returned: {frame['tic'].nunique():,}")
    if not coverage.empty:
        print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()
