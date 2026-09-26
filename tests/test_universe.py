import pandas as pd

from market_analyzer.data.universe import UniverseConfig, build_universe_registry, eligible_tickers_on

def _frame():
    sessions = pd.date_range("2024-01-01", periods=10, freq="D")
    rows = []
    for tic, start, count, price in [
        ("GOOD", 0, 10, 100),
        ("NEWCO", 5, 5, 100),
        ("NIFTYETF", 0, 10, 100),
    ]:
        for day in sessions[start:start + count]:
            rows.append({
                "date": day, "tic": tic, "open": price, "high": price + 1,
                "low": price - 1, "close": price, "volume": 200_000,
            })
    return pd.DataFrame(rows), sessions

def test_registry_applies_history_coverage_liquidity_and_symbol_screen():
    frame, sessions = _frame()
    config = UniverseConfig(min_history_sessions=6, min_coverage_ratio=0.8, min_median_turnover=10_000_000)
    registry = build_universe_registry(frame, sessions, config).set_index("tic")
    assert bool(registry.loc["GOOD", "eligible"])
    assert not bool(registry.loc["NEWCO", "eligible"])
    assert "insufficient_history" in registry.loc["NEWCO", "reason"]
    assert not bool(registry.loc["NIFTYETF", "eligible"])
    assert registry.loc["NIFTYETF", "instrument_class"] == "screened_non_equity"

def test_point_in_time_universe_does_not_use_future_rows():
    frame, sessions = _frame()
    config = UniverseConfig(min_history_sessions=6, min_coverage_ratio=0.8, min_median_turnover=10_000_000)
    assert "NEWCO" not in eligible_tickers_on(frame, "2024-01-10", sessions, config)
    assert eligible_tickers_on(frame, "2024-01-10", sessions, config) == ["GOOD"]

def test_registry_requires_normalized_market_columns():
    try:
        build_universe_registry(pd.DataFrame({"date": ["2024-01-01"], "tic": ["GOOD"]}))
    except ValueError as exc:
        assert "Missing market columns" in str(exc)
    else:
        raise AssertionError("expected missing-column validation error")
