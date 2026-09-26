import numpy as np
import pandas as pd

from market_analyzer.features.engineering import FeatureEngineer


def test_turbulence_handles_single_asset_covariance_after_missing_data():
    dates = pd.date_range("2020-01-01", periods=80, freq="D")
    rows = []
    for tic, seed in [("AAA", 1), ("BBB", 2)]:
        rng = np.random.default_rng(seed)
        close = 100 * np.cumprod(1 + rng.normal(0, 0.01, len(dates)))
        for date, price in zip(dates, close):
            rows.append({"date": date, "tic": tic, "open": price, "high": price, "low": price, "close": price, "volume": 1000.0})
    frame = pd.DataFrame(rows)
    # Make one asset unavailable on a date after the turbulence warm-up so
    # the covariance can temporarily collapse to a single dimension.
    frame = frame[~((frame["tic"] == "BBB") & (frame["date"] == dates[70]))]
    out = FeatureEngineer(include_vix=False, include_turbulence=True).transform(frame)
    assert "turbulence" in out.columns
    assert np.isfinite(out["turbulence"].dropna()).all()
