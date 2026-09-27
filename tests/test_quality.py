import pandas as pd
import pytest

from market_analyzer.data.quality import classify_jump_context


def test_classify_jump_context_exact_action():
    frame = pd.DataFrame([
        {"date":"2026-01-01","tic":"ABC","close":100},
        {"date":"2026-01-02","tic":"ABC","close":200},
    ])
    jumps = pd.DataFrame([{
        "tic":"ABC","date":pd.Timestamp("2026-01-02"),
        "previous_close":100.0,"close":200.0,"jump_pct":100.0,
    }])
    actions = pd.DataFrame([{
        "tic":"ABC","ex_date":pd.Timestamp("2026-01-02"),
        "purpose":"Bonus 1:1","price_factor":0.5,"adjustment_type":"bonus",
    }])
    sessions = pd.date_range("2026-01-01", "2026-01-02", freq="D")
    result = classify_jump_context(jumps, frame, actions, sessions)
    assert result.iloc[0]["classification"] == "exact_action"


def test_classify_jump_context_post_gap():
    frame = pd.DataFrame([
        {"date":"2026-01-01","tic":"ABC","close":100},
        {"date":"2026-01-06","tic":"ABC","close":200},
    ])
    jumps = pd.DataFrame([{
        "tic":"ABC","date":pd.Timestamp("2026-01-06"),
        "previous_close":100.0,"close":200.0,"jump_pct":100.0,
    }])
    actions = pd.DataFrame(columns=["tic","ex_date","purpose","price_factor","adjustment_type"])
    sessions = pd.date_range("2026-01-01", "2026-01-06", freq="D")
    result = classify_jump_context(jumps, frame, actions, sessions)
    assert result.iloc[0]["classification"] == "post_gap"
    assert result.iloc[0]["gap_sessions"] == 4


def test_classify_jump_context_near_action_and_gap():
    frame = pd.DataFrame([
        {"date":"2026-01-01","tic":"ABC","close":100},
        {"date":"2026-01-06","tic":"ABC","close":200},
    ])
    jumps = pd.DataFrame([{
        "tic":"ABC","date":pd.Timestamp("2026-01-06"),
        "previous_close":100.0,"close":200.0,"jump_pct":100.0,
    }])
    actions = pd.DataFrame([{
        "tic":"ABC","ex_date":pd.Timestamp("2026-01-08"),
        "purpose":"Demerger","price_factor":None,"adjustment_type":"review",
    }])
    sessions = pd.date_range("2026-01-01", "2026-01-08", freq="D")
    result = classify_jump_context(jumps, frame, actions, sessions, action_window_days=5)
    assert result.iloc[0]["classification"] == "near_action_and_post_gap"


def test_classify_jump_context_unexplained():
    frame = pd.DataFrame([
        {"date":"2026-01-01","tic":"ABC","close":100},
        {"date":"2026-01-02","tic":"ABC","close":200},
    ])
    jumps = pd.DataFrame([{
        "tic":"ABC","date":pd.Timestamp("2026-01-02"),
        "previous_close":100.0,"close":200.0,"jump_pct":100.0,
    }])
    actions = pd.DataFrame(columns=["tic","ex_date","purpose","price_factor","adjustment_type"])
    sessions = pd.date_range("2026-01-01", "2026-01-02", freq="D")
    result = classify_jump_context(jumps, frame, actions, sessions)
    assert result.iloc[0]["classification"] == "unexplained"
