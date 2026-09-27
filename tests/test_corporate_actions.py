import pandas as pd
import pytest

from market_analyzer.data.corporate_actions import (
    apply_backward_adjustments,
    parse_corporate_action,
    parse_corporate_actions,
    build_adjusted_research_frame,
)


def test_parse_bonus_ratio():
    action = parse_corporate_action("ABC", "2026-01-10", "Bonus 1:1")
    assert action.adjustment_type == "bonus"
    assert action.price_factor == pytest.approx(0.5)


def test_parse_bonus_two_for_one():
    action = parse_corporate_action("ABC", "2026-01-10", "Bonus 1:2")
    assert action.price_factor == pytest.approx(2 / 3)


def test_parse_face_value_split():
    action = parse_corporate_action(
        "ABC", "2026-01-10",
        "Face Value Split (Sub-Division) - From Rs 5/- Per Share To Re 1/- Per Share",
    )
    assert action.adjustment_type == "split"
    assert action.price_factor == pytest.approx(0.2)


def test_unambiguous_actions_adjust_only_pre_ex_date():
    prices = pd.DataFrame([
        {"date":"2026-01-09","tic":"ABC","open":100.0,"high":105.0,"low":95.0,"close":100.0,"volume":1000},
        {"date":"2026-01-10","tic":"ABC","open":50.0,"high":52.0,"low":48.0,"close":50.0,"volume":2000},
    ])
    actions = parse_corporate_actions(pd.DataFrame([
        {"symbol":"ABC","ex_date":"2026-01-10","purpose":"Bonus 1:1"},
    ]))
    adjusted = apply_backward_adjustments(prices, actions)
    assert adjusted.iloc[0]["close"] == pytest.approx(50.0)
    assert adjusted.iloc[0]["volume"] == pytest.approx(2000.0)
    assert adjusted.iloc[1]["close"] == pytest.approx(50.0)


def test_ambiguous_action_is_not_automatically_adjusted():
    action = parse_corporate_action("ABC", "2026-01-10", "Demerger")
    assert action.adjustment_type == "review"
    assert action.price_factor is None


def test_ratio_only_split_is_review_only():
    action = parse_corporate_action("ABC", "2026-01-10", "Split 1:5")
    assert action.adjustment_type == "review"
    assert action.price_factor is None


def test_abbreviated_face_value_split_is_adjustable():
    action = parse_corporate_action("ABC", "2026-01-10", "Fv Splt Frm Rs 10 To Rs 2")
    assert action.adjustment_type == "split"
    assert action.price_factor == pytest.approx(0.2)


def test_composite_bonus_face_value_split_uses_combined_factor():
    action = parse_corporate_action(
        "ABC", "2026-01-10",
        "Bonus 1:1/Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share",
    )
    assert action.adjustment_type == "bonus"
    assert action.price_factor == pytest.approx(0.5 * 0.2)


def test_bonus_ncrps_is_review_only():
    action = parse_corporate_action("ABC", "2026-01-10", "Scheme Of Arrangement - Bonus Ncrps 4:1")
    assert action.adjustment_type == "review"
    assert action.price_factor is None


def test_adjusted_research_frame_is_non_destructive_and_cumulative():
    prices = pd.DataFrame([
        {"date":"2026-01-08","tic":"ABC","open":100.0,"high":105.0,"low":95.0,"close":100.0,"volume":1000},
        {"date":"2026-01-10","tic":"ABC","open":50.0,"high":52.0,"low":48.0,"close":50.0,"volume":2000},
        {"date":"2026-01-12","tic":"ABC","open":25.0,"high":26.0,"low":24.0,"close":25.0,"volume":4000},
    ])
    original = prices.copy(deep=True)
    actions = parse_corporate_actions(pd.DataFrame([
        {"symbol":"ABC","ex_date":"2026-01-10","purpose":"Bonus 1:1"},
        {"symbol":"ABC","ex_date":"2026-01-12","purpose":"Face Value Split (Sub-Division) - From Rs 2/- Per Share To Re 1/- Per Share"},
    ]))
    adjusted = build_adjusted_research_frame(prices, actions)
    assert prices.equals(original)
    assert adjusted.loc[adjusted["date"] == "2026-01-08", "close"].iloc[0] == pytest.approx(25.0)
    assert adjusted.loc[adjusted["date"] == "2026-01-10", "close"].iloc[0] == pytest.approx(25.0)
    assert adjusted.loc[adjusted["date"] == "2026-01-12", "close"].iloc[0] == pytest.approx(25.0)
    assert adjusted["price_adjusted"].all()
