import pandas as pd

from market_analyzer.data.fundamentals import FundamentalSnapshot, merge_fundamentals_asof

def test_fundamentals_asof_merge_is_sorted_by_timestamp():
    market = pd.DataFrame({
        "date": ["2025-01-02", "2025-01-01", "2025-01-02", "2025-01-01"],
        "tic": ["AAA", "AAA", "BBB", "BBB"],
        "close": [10, 9, 20, 19],
    })
    snapshots = [
        FundamentalSnapshot("AAA", pd.Timestamp("2024-12-01", tz="UTC"), pd.Timestamp("2024-12-15", tz="UTC"), "test", {"revenue": 100}),
        FundamentalSnapshot("BBB", pd.Timestamp("2024-12-01", tz="UTC"), pd.Timestamp("2024-12-20", tz="UTC"), "test", {"revenue": 200}),
    ]
    out = merge_fundamentals_asof(market, snapshots)
    assert len(out) == len(market)
    assert out["fund_revenue"].notna().all()
