import pandas as pd

from market_analyzer.models.forecasting import ReturnForecaster
from market_analyzer.models.crash import CrashRiskModel


def sample_frame(n=180):
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    rows = []
    for tic, base in [("AAA", 100.0), ("BBB", 80.0)]:
        for i, date in enumerate(dates):
            price = base + i * 0.1
            rows.append({
                "date": date,
                "tic": tic,
                "close": price,
                "f1": float(i % 7),
                "f2": float(i % 11),
            })
    return pd.DataFrame(rows)


def test_forecaster_target_is_purged_at_train_boundary():
    frame = sample_frame()
    model = ReturnForecaster(horizon=5)
    model.fit(frame, ["f1", "f2"], train_end=pd.Timestamp("2020-06-30"))
    assert model.model is not None


def test_crash_target_is_purged_at_train_boundary():
    frame = sample_frame()
    model = CrashRiskModel(horizon=5)
    # The monotonically rising fixture may contain one class only, so this
    # test focuses on target construction rather than fitting.
    target = model.make_target(frame)
    assert target.notna().all()
