import numpy as np
import pandas as pd

from market_analyzer.models.multihorizon import MultiHorizonForecaster


def sample_frame(n=180):
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    rng = np.random.default_rng(4)
    rows = []
    for tic, base in [("AAA", 100.0), ("BBB", 80.0)]:
        close = base * np.cumprod(1 + rng.normal(0.0005, 0.01, n))
        for i, (date, price) in enumerate(zip(dates, close)):
            rows.append({
                "date": date,
                "tic": tic,
                "close": price,
                "f1": rng.normal(),
                "f2": rng.normal(),
            })
    return pd.DataFrame(rows)


def test_multihorizon_prediction_columns():
    frame = sample_frame()
    model = MultiHorizonForecaster(horizons=(1, 5))
    model.fit(frame, ["f1", "f2"], train_end=pd.Timestamp("2020-06-30"))
    out = model.predict(frame)
    assert {"expected_return_1d", "expected_return_5d"}.issubset(out.columns)
    assert len(out) > 0
