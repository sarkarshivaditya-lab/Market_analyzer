"""Audit a previously populated local NSE SQLite store."""
from __future__ import annotations

import argparse
import pandas as pd

from market_analyzer.data.local import NSELocalMarketStore
from market_analyzer.data.quality import audit_market_data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="data/market/nse.sqlite")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--tickers", nargs="*", default=None)
    args = parser.parse_args()

    store = NSELocalMarketStore(args.store)
    frame = store.load(args.start, args.end, args.tickers)
    report = audit_market_data(frame)
    print(report.to_dict())
    print()
    print(store.coverage(args.tickers).to_string(index=False) if not store.coverage(args.tickers).empty else "No stored coverage.")


if __name__ == "__main__":
    main()
