"""Reconcile NSE price-jump candidates against an NSE corporate-action CSV."""
from __future__ import annotations

import argparse
import pandas as pd

from market_analyzer.data.local import NSELocalMarketStore
from market_analyzer.data.corporate_actions import parse_corporate_actions
from market_analyzer.data.quality import price_jump_details


def _normalize_actions(frame: pd.DataFrame) -> pd.DataFrame:
    columns = {str(column).strip().lower().replace(" ", "_").replace("-", "_"): column for column in frame.columns}
    aliases = {
        "symbol": ["symbol", "security_symbol"],
        "ex_date": ["ex_date", "exdate"],
        "purpose": ["purpose", "corporate_action_description"],
    }
    selected = {}
    for target, names in aliases.items():
        source = next((columns[name] for name in names if name in columns), None)
        if source is None:
            raise ValueError(f"Corporate-action CSV is missing {target}")
        selected[target] = source
    return frame.rename(columns={v: k for k, v in selected.items()})[list(aliases)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="data/market/nse.sqlite")
    parser.add_argument("--actions", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args()

    store = NSELocalMarketStore(args.store)
    market = store.load(args.start, args.end)
    jumps = price_jump_details(market)
    actions = parse_corporate_actions(_normalize_actions(pd.read_csv(args.actions)))
    usable = actions.dropna(subset=["ex_date", "price_factor"]).copy()

    jumps["date"] = pd.to_datetime(jumps["date"])
    matched = jumps.merge(
        usable[["tic", "ex_date", "purpose", "price_factor", "adjustment_type"]],
        left_on=["tic", "date"],
        right_on=["tic", "ex_date"],
        how="left",
    )
    matched["matched_action"] = matched["purpose"].notna()
    matched["abs_jump_pct"] = matched["jump_pct"].abs()
    matched = matched.sort_values("abs_jump_pct", ascending=False)

    print(f"price_jump_candidates={len(jumps)}")
    print(f"parsed_actions={len(actions)}")
    print(f"automatically_adjustable_actions={len(usable)}")
    print(f"jumps_matching_unambiguous_action={int(matched['matched_action'].sum())}")
    print("=== TOP JUMPS WITH CORPORATE-ACTION MATCHES ===")
    print(
        matched.head(max(args.top, 0))[[
            "tic", "date", "jump_pct", "purpose", "price_factor", "adjustment_type"
        ]].to_string(index=False)
        if not matched.empty else "None."
    )


if __name__ == "__main__":
    main()
