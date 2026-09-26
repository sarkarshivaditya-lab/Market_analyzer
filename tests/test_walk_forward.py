import pandas as pd

from market_analyzer.data.macro import MacroData
from market_analyzer.training.walk_forward import walk_forward_windows


def test_walk_forward_purges_horizon():
    dates = pd.date_range("2020-01-01", periods=1000, freq="B")
    windows = list(walk_forward_windows(dates, min_train_days=756, test_days=21, horizon_days=20))
    assert windows
    assert windows[0].test_start > windows[0].train_end
    assert (windows[0].test_start - windows[0].train_end).days >= 20


def test_walk_forward_accepts_series_dates():
    dates = pd.Series(pd.date_range("2020-01-01", periods=1000, freq="B"))
    windows = list(walk_forward_windows(dates, min_train_days=756, test_days=21, horizon_days=20))
    assert windows


def test_macro_merge_does_not_create_tic_rows():
    market = pd.DataFrame({
        "date": ["2024-01-02", "2024-01-03"],
        "tic": ["AAA", "AAA"],
        "close": [100.0, 101.0],
    })
    macro = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-03"]),
        "macro_vix": [14.0, 18.0],
    })
    out = MacroData.merge_asof(market, macro)
    assert len(out) == len(market)
    assert out["tic"].tolist() == ["AAA", "AAA"]
    assert out.loc[0, "macro_vix"] == 14.0


def test_macro_name():
    assert MacroData._name("^TNX") == "tnx"
