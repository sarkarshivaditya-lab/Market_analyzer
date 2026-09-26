import pandas as pd
import pytest

from market_analyzer.data.corporate_actions import (
    apply_backward_adjustments,
    parse_corporate_action,
    parse_corporate_actions,
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
