import pandas as pd

from market_analyzer.data.local import NSELocalMarketStore


def test_nse_local_store_upserts_and_queries(tmp_path):
    store = NSELocalMarketStore(tmp_path / "nse.sqlite")
    frame = pd.DataFrame([
        {"date":"2026-09-24","tic":"INFY","open":1500,"high":1520,"low":1490,"close":1510,"volume":100000},
        {"date":"2026-09-25","tic":"INFY","open":1510,"high":1530,"low":1505,"close":1525,"volume":120000},
        {"date":"2026-09-25","tic":"TCS","open":3000,"high":3050,"low":2990,"close":3030,"volume":200000},
    ])
    assert store.upsert(frame) == 3
    assert store.upsert(frame.iloc[[1]]) == 1
    out = store.load("2026-09-24", "2026-09-26", ["INFY"])
    assert out[["date","tic"]].to_records(index=False).tolist() == [
        ("2026-09-24","INFY"),("2026-09-25","INFY")
    ]
    assert out.iloc[-1]["close"] == 1525


def test_nse_local_store_reports_coverage(tmp_path):
    store = NSELocalMarketStore(tmp_path / "nse.sqlite")
    store.upsert(pd.DataFrame([{
        "date":"2026-09-25","tic":"RELIANCE","open":1,"high":2,
        "low":0.5,"close":1.5,"volume":10
    }]))
    coverage = store.coverage()
    assert coverage.to_dict("records") == [{
        "tic":"RELIANCE","first_date":"2026-09-25","last_date":"2026-09-25","rows":1
    }]
