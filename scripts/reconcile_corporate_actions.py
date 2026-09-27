"""Reconcile NSE price jumps against corporate actions, with resumable NSE acquisition."""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

from market_analyzer.data.local import NSELocalMarketStore
from market_analyzer.data.corporate_actions import parse_corporate_actions
from market_analyzer.data.quality import price_jump_details

BASE_URL = "https://www.nseindia.com"
ACTIONS_URL = BASE_URL + "/api/corporates-corporateActions"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
    "Referer": BASE_URL + "/",
}


def _normalize_actions(frame: pd.DataFrame) -> pd.DataFrame:
    columns = {str(column).strip().lower().replace(" ", "_").replace("-", "_"): column for column in frame.columns}
    aliases = {
        "symbol": ["symbol", "security_symbol"],
        "ex_date": ["ex_date", "exdate"],
        "purpose": ["purpose", "corporate_action_description", "subject", "description"],
    }
    selected = {}
    for target, names in aliases.items():
        source = next((columns[name] for name in names if name in columns), None)
        if source is None:
            raise ValueError(f"Corporate-action CSV is missing {target}")
        selected[target] = source
    return frame.rename(columns={v: k for k, v in selected.items()})[list(aliases)]


def _load_universe(path: str) -> list[str]:
    frame = pd.read_csv(path)
    if "tic" not in frame.columns:
        raise ValueError(f"Universe file {path} must contain tic")
    if "eligible" in frame.columns:
        frame = frame[frame["eligible"].astype(str).str.lower().eq("true")]
    return sorted(frame["tic"].astype(str).str.strip().str.upper().dropna().unique())


def _safe_symbol(symbol: str) -> str:
    return re.sub(r"[^A-Z0-9_.-]+", "_", symbol.upper())


def _extract_api_rows(payload: object, symbol: str) -> list[dict]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("data") or payload.get("corporateActions") or payload.get("corporate_actions") or []
    else:
        rows = []
    return [dict(row, symbol=row.get("symbol", symbol)) for row in rows if isinstance(row, dict)]


def _fetch_api_symbol(session: requests.Session, symbol: str) -> list[dict]:
    response = session.get(
        ACTIONS_URL,
        params={"index": "equities", "symbol": symbol},
        timeout=30,
    )
    response.raise_for_status()
    return _extract_api_rows(response.json(), symbol)


def fetch_nse_actions(
    universe_path: str,
    cache_dir: str,
    output_path: str,
    limit: int = 0,
    delay: float = 0.35,
    max_retries: int = 3,
) -> pd.DataFrame:
    symbols = _load_universe(universe_path)
    if limit > 0:
        symbols = symbols[:limit]
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(BASE_URL, timeout=30)
    rows: list[dict] = []
    fetched = cached = 0
    failed: list[str] = []

    for symbol in symbols:
        cache_path = cache / f"{_safe_symbol(symbol)}.json"
        data = None
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text())
                cached += 1
            except (OSError, json.JSONDecodeError):
                data = None
        if data is None:
            for attempt in range(max_retries):
                try:
                    data = _fetch_api_symbol(session, symbol)
                    cache_path.write_text(json.dumps(data, ensure_ascii=False))
                    fetched += 1
                    break
                except (requests.RequestException, ValueError) as exc:
                    if attempt + 1 == max_retries:
                        failed.append(f"{symbol}: {exc}")
                    else:
                        time.sleep(min(2 ** attempt, 8))
        if data is not None:
            rows.extend(data)
        time.sleep(max(delay, 0))

    if rows:
        frame = pd.DataFrame(rows)
        columns = {str(c).strip().lower().replace(" ", "_").replace("-", "_"): c for c in frame.columns}
        aliases = {
            "symbol": ["symbol", "security_symbol"],
            "ex_date": ["ex_date", "exdate", "ex_date_"],
            "purpose": ["purpose", "subject", "description", "corporate_action_description"],
        }
        for target, names in aliases.items():
            source = next((columns[n] for n in names if n in columns), None)
            frame[target] = frame[source] if source else pd.NA
        frame = frame[["symbol", "ex_date", "purpose"]]
        frame["symbol"] = frame["symbol"].astype("string").str.strip().str.upper()
        frame["ex_date"] = pd.to_datetime(frame["ex_date"], errors="coerce", dayfirst=True)
        frame["purpose"] = frame["purpose"].astype("string").fillna("").str.strip()
        frame = frame.drop_duplicates()
    else:
        frame = pd.DataFrame(columns=["symbol", "ex_date", "purpose"])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    print(f"symbols_requested={len(symbols)}")
    print(f"symbols_fetched={fetched}")
    print(f"symbols_cached={cached}")
    print(f"symbols_failed={len(failed)}")
    print(f"corporate_action_rows={len(frame)}")
    dates = frame["ex_date"].dropna()
    if not dates.empty:
        print(f"ex_date_range={dates.min().date()} -> {dates.max().date()}")
    if failed:
        print("=== FAILED SYMBOLS ===")
        print("\n".join(failed[:50]))
    return frame


def reconcile(store_path: str, actions_path: str, start: str, end: str, top: int) -> None:
    store = NSELocalMarketStore(store_path)
    market = store.load(start, end)
    jumps = price_jump_details(market)
    actions = parse_corporate_actions(_normalize_actions(pd.read_csv(actions_path)))
    usable = actions.dropna(subset=["ex_date", "price_factor"]).copy()
    jumps["date"] = pd.to_datetime(jumps["date"])
    all_actions = actions[["tic", "ex_date", "purpose", "price_factor", "adjustment_type"]].copy()
    all_actions["ex_date"] = pd.to_datetime(all_actions["ex_date"], errors="coerce")
    matched = jumps.merge(
        all_actions,
        left_on=["tic", "date"],
        right_on=["tic", "ex_date"],
        how="left",
    )
    matched["matched_action"] = matched["purpose"].notna()
    matched["adjustable_match"] = matched["matched_action"] & matched["price_factor"].notna()
    matched["abs_jump_pct"] = matched["jump_pct"].abs()
    matched = matched.sort_values("abs_jump_pct", ascending=False)
    print(f"price_jump_candidates={len(jumps)}")
    print(f"parsed_actions={len(actions)}")
    print(f"automatically_adjustable_actions={len(usable)}")
    print(f"jumps_matching_any_action={int(matched['matched_action'].sum())}")
    print(f"jumps_matching_adjustable_action={int(matched['adjustable_match'].sum())}")
    print("=== TOP JUMPS WITH CORPORATE-ACTION CLASSIFICATION ===")
    print(
        matched.head(max(top, 0))[["tic", "date", "jump_pct", "purpose", "price_factor", "adjustment_type", "adjustable_match"]].to_string(index=False)
        if not matched.empty else "None."
    )
    print("=== MATCH CLASSIFICATION ===")
    if matched["matched_action"].any():
        summary = matched.loc[matched["matched_action"]].groupby("adjustment_type", dropna=False).size().sort_values(ascending=False)
        print(summary.to_string())
    else:
        print("No exact jump/action matches.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="data/market/nse.sqlite")
    parser.add_argument("--actions")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2026-09-27")
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--fetch-universe")
    parser.add_argument("--fetch-output", default="data/raw/nse/corporate_actions_api.csv")
    parser.add_argument("--fetch-cache", default="data/raw/nse/corporate_actions_api")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0.35)
    args = parser.parse_args()

    if args.fetch_universe:
        fetch_nse_actions(
            args.fetch_universe,
            args.fetch_cache,
            args.fetch_output,
            limit=args.limit,
            delay=args.delay,
        )
        return
    if not args.actions:
        parser.error("--actions is required unless --fetch-universe is supplied")
    reconcile(args.store, args.actions, args.start, args.end, args.top)


if __name__ == "__main__":
    main()
