import pandas as pd

from market_analyzer.data.universe import UniverseConfig, eligible_tickers_on


def test_point_in_time_audit_logic_uses_only_rows_on_or_before_as_of():
    sessions = pd.date_range("2024-01-01", periods=12, freq="D")
    rows = []
    for day in sessions:
        rows.append({
            "date": day,
            "tic": "OLD",
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "volume": 200_000,
        })
    for day in sessions[6:]:
        rows.append({
            "date": day,
            "tic": "LATE",
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "volume": 200_000,
        })
    frame = pd.DataFrame(rows)
    config = UniverseConfig(
        min_history_sessions=6,
        min_coverage_ratio=0.70,
        min_median_turnover=10_000_000,
    )
    before_listing = eligible_tickers_on(frame, "2024-01-06", sessions, config)
    after_listing = eligible_tickers_on(frame, "2024-01-12", sessions, config)
    assert before_listing == ["OLD"]
    assert after_listing == ["LATE", "OLD"]
