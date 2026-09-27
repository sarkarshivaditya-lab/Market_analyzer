#!/usr/bin/env python3
"""Classify continuity gaps and residual price jumps in the adjusted NSE research store."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from market_analyzer.data.corporate_actions import parse_corporate_actions
from market_analyzer.data.local import NSELocalMarketStore
from market_analyzer.data.quality import classify_jump_context, price_jump_details


def _gap_runs(frame: pd.DataFrame, sessions: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    sessions = pd.DatetimeIndex(sessions).normalize().sort_values().unique()
    for tic, group in frame.groupby("tic", sort=True):
        observed = pd.DatetimeIndex(pd.to_datetime(group["date"]).dt.normalize().unique())
        if not len(observed):
            continue
        expected = sessions[(sessions >= observed.min()) & (sessions <= observed.max())]
        missing = expected.difference(observed)
        if not len(missing):
            continue
        missing = pd.Series(missing).sort_values().reset_index(drop=True)
        start = missing.iloc[0]
        prev = missing.iloc[0]
        runs = []
        for value in missing.iloc[1:]:
            pos = expected.get_indexer([prev])[0]
            next_pos = expected.get_indexer([value])[0]
            if next_pos == pos + 1:
                prev = value
            else:
                runs.append((start, prev))
                start = prev = value
        runs.append((start, prev))
        for run_start, run_end in runs:
            rows.append({
                "tic": tic,
                "gap_start": run_start.strftime("%Y-%m-%d"),
                "gap_end": run_end.strftime("%Y-%m-%d"),
                "missing_sessions": int(expected[(expected >= run_start) & (expected <= run_end)].size),
            })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="data/market/nse_adjusted.sqlite")
    parser.add_argument("--actions", default="data/raw/nse/corporate_actions_api.csv")
    parser.add_argument("--universe", default="data/market/nse_universe.csv")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2026-09-27")
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args()

    store = NSELocalMarketStore(args.store)
    frame = store.load(args.start, args.end)
    registry = pd.read_csv(args.universe)
    eligible = registry.loc[registry["eligible"].astype(bool), "tic"].astype(str).str.upper().unique()
    frame = frame[frame["tic"].astype(str).str.upper().isin(eligible)].copy()
    sessions = pd.DatetimeIndex(frame["date"].unique()).sort_values()

    print("=== ELIGIBLE CONTINUITY CLASSIFICATION ===")
    runs = _gap_runs(frame, sessions)
    print(f"gap_runs={len(runs)}")
    if not runs.empty:
        print(f"tickers_with_gaps={runs['tic'].nunique()}")
        print(f"total_missing_sessions={int(runs['missing_sessions'].sum())}")
        print("longest_gap_runs=")
        print(runs.sort_values("missing_sessions", ascending=False).head(args.top).to_string(index=False))

    jumps = price_jump_details(frame)
    actions_raw = pd.read_csv(args.actions)
    actions = parse_corporate_actions(actions_raw)
    actions["ex_date"] = pd.to_datetime(actions["ex_date"], errors="coerce")
    actions["tic"] = actions["tic"].astype(str).str.upper()
    jumps["date"] = pd.to_datetime(jumps["date"])
    matched = jumps.merge(
        actions[["tic", "ex_date", "purpose", "price_factor", "adjustment_type"]],
        left_on=["tic", "date"],
        right_on=["tic", "ex_date"],
        how="left",
    )
    matched["exact_action_match"] = matched["purpose"].notna()
    print()
    print("=== RESIDUAL PRICE-JUMP CLASSIFICATION ===")
    print(f"jump_candidates={len(jumps)}")
    print(f"exact_action_matches={int(matched['exact_action_match'].sum())}")
    print(f"adjustable_action_matches={int(matched['price_factor'].notna().sum())}")
    print("adjustment_type_counts=")
    print(
        matched.loc[matched["exact_action_match"], "adjustment_type"]
        .fillna("unknown")
        .value_counts()
        .to_string()
        if matched["exact_action_match"].any() else "None."
    )
    print("exact_matches=")
    exact = matched[matched["exact_action_match"]]
    print(
        exact[["tic", "date", "previous_close", "close", "jump_pct", "purpose", "price_factor", "adjustment_type"]]
        .sort_values("jump_pct", key=lambda values: values.abs(), ascending=False)
        .to_string(index=False)
        if not exact.empty else "None."
    )
    print("largest_unmatched=")
    unmatched = matched[~matched["exact_action_match"]]
    print(
        unmatched[["tic", "date", "previous_close", "close", "jump_pct"]]
        .head(args.top).to_string(index=False)
        if not unmatched.empty else "None."
    )

    context = classify_jump_context(jumps, frame, actions, sessions)
    print()
    print("=== RESIDUAL CONTEXT CLASSIFICATION ===")
    print(context["classification"].value_counts().sort_index().to_string())
    print("context_top=")
    columns = [
        "tic", "date", "jump_pct", "classification", "gap_sessions",
        "previous_observation", "nearest_action_date", "nearest_action_days",
        "nearest_action_purpose", "nearest_action_type", "nearest_action_factor",
    ]
    print(context[columns].head(args.top).to_string(index=False) if not context.empty else "None.")


if __name__ == "__main__":
    main()
