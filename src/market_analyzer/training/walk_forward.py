"""Chronological walk-forward splitting with purge/embargo protection."""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
from market_analyzer.data.universe import UniverseConfig, eligible_tickers_on


@dataclass(frozen=True)
class WalkForwardWindow:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def walk_forward_windows(
    dates,
    min_train_days: int = 756,
    test_days: int = 21,
    horizon_days: int = 5,
    step_days: int | None = None,
):
    """Yield expanding-window train/test periods.

    The training set ends before the test period by at least horizon_days.
    This purge prevents a forward-return target at the train boundary from
    consuming observations that belong to the test period.
    """
    unique = pd.DatetimeIndex(pd.to_datetime(dates)).normalize().unique().sort_values()
    if len(unique) < min_train_days + horizon_days + test_days:
        return
    step_days = step_days or test_days
    train_end_idx = min_train_days - 1
    while train_end_idx + horizon_days + 1 < len(unique):
        test_start_idx = train_end_idx + horizon_days + 1
        test_end_idx = min(test_start_idx + test_days - 1, len(unique) - 1)
        yield WalkForwardWindow(
            train_start=unique[0],
            train_end=unique[train_end_idx],
            test_start=unique[test_start_idx],
            test_end=unique[test_end_idx],
        )
        if test_end_idx >= len(unique) - 1:
            break
        train_end_idx += step_days


def split_frame(
    frame: pd.DataFrame,
    window: WalkForwardWindow,
    universe_frame: pd.DataFrame | None = None,
    universe_config: UniverseConfig | None = None,
):
    dates = pd.to_datetime(frame["date"])
    train = frame[(dates >= window.train_start) & (dates <= window.train_end)].copy()
    test = frame[(dates >= window.test_start) & (dates <= window.test_end)].copy()
    if universe_frame is not None:
        config = universe_config or UniverseConfig()
        sessions = pd.DatetimeIndex(pd.to_datetime(universe_frame["date"])).normalize().unique().sort_values()
        train_tickers = set(eligible_tickers_on(universe_frame, window.train_end, sessions, config))
        test_tickers = set(eligible_tickers_on(universe_frame, window.test_start, sessions, config))
        train = train[train["tic"].isin(train_tickers)].copy()
        test = test[test["tic"].isin(test_tickers)].copy()
    return train, test
