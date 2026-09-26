import pandas as pd
import pytest

from market_analyzer.data.quality import audit_market_data, price_jump_details, ticker_gap_details


def _frame():
    return pd.DataFrame([
        {"date":"2026-09-24","tic":"INFY","open":1500,"high":1520,"low":1490,"close":1510,"volume":100},
        {"date":"2026-09-25","tic":"INFY","open":1510,"high":1530,"low":1505,"close":1525,"volume":120},
        {"date":"2026-09-24","tic":"TCS","open":3000,"high":3050,"low":2990,"close":3030,"volume":200},
    ])


def test_market_quality_report_accepts_clean_data():
    report = audit_market_data(_frame())
    assert report.valid
    assert report.rows == 3
    assert report.tickers == 2
    assert report.first_date == "2026-09-24"
    assert report.last_date == "2026-09-25"
    assert report.price_jump_candidates == 0


def test_market_quality_report_detects_market_data_anomalies():
    frame = _frame()
    frame.loc[1, "high"] = 1400
    frame.loc[2, "volume"] = -1
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    report = audit_market_data(frame)
    assert not report.valid
    assert report.duplicate_rows == 2
    assert report.invalid_ohlc_rows == 1
    assert report.negative_volume_rows == 1


def test_market_quality_report_counts_missing_sessions_within_active_history():
    frame = pd.DataFrame([
        {"date":"2026-09-24","tic":"INFY","open":1500,"high":1520,"low":1490,"close":1510,"volume":100},
        {"date":"2026-09-25","tic":"INFY","open":1510,"high":1530,"low":1505,"close":1525,"volume":120},
        {"date":"2026-09-24","tic":"TCS","open":3000,"high":3050,"low":2990,"close":3030,"volume":200},
        {"date":"2026-09-26","tic":"TCS","open":3030,"high":3080,"low":3020,"close":3050,"volume":200},
    ])
    sessions = pd.DatetimeIndex(["2026-09-24", "2026-09-25", "2026-09-26"])
    report = audit_market_data(frame, expected_sessions=sessions)
    assert report.ticker_date_gaps == 1


def test_market_quality_requires_normalized_market_columns():
    with pytest.raises(ValueError, match="Missing market columns"):
        audit_market_data(pd.DataFrame({"date":["2026-09-24"], "tic":["INFY"]}))


def test_market_quality_flags_large_price_discontinuities_without_marking_data_invalid():
    frame = _frame()
    frame.loc[1, ["open", "high", "low", "close"]] = [2990, 3010, 2980, 3000]
    report = audit_market_data(frame)
    assert report.valid
    assert report.price_jump_candidates == 1

def test_market_quality_gap_audit_ignores_pre_listing_and_post_delisting_sessions():
    frame = pd.DataFrame([
        {"date":"2026-09-24","tic":"NEWCO","open":100,"high":101,"low":99,"close":100,"volume":100},
        {"date":"2026-09-26","tic":"NEWCO","open":101,"high":102,"low":100,"close":101,"volume":100},
    ])
    sessions = pd.DatetimeIndex(["2026-09-20","2026-09-21","2026-09-22","2026-09-23","2026-09-24","2026-09-25","2026-09-26","2026-09-27"])
    report = audit_market_data(frame, expected_sessions=sessions)
    assert report.ticker_date_gaps == 1

def test_price_jump_details_exposes_candidate_rows():
    frame = _frame()
    frame.loc[1, ["open", "high", "low", "close"]] = [2990, 3010, 2980, 3000]
    details = price_jump_details(frame)
    assert len(details) == 1
    assert details.loc[0, "tic"] == "INFY"
    assert details.loc[0, "previous_close"] == 1510
    assert details.loc[0, "close"] == 3000


def test_ticker_gap_details_reports_missing_active_sessions():
    frame = pd.DataFrame([
        {"date":"2026-09-24","tic":"INFY"},
        {"date":"2026-09-25","tic":"INFY"},
        {"date":"2026-09-24","tic":"TCS"},
        {"date":"2026-09-26","tic":"TCS"},
    ])
    sessions = pd.DatetimeIndex(["2026-09-24", "2026-09-25", "2026-09-26"])
    details = ticker_gap_details(frame, sessions)
    assert details.to_dict("records") == [{"tic": "TCS", "missing_sessions": 1}]
