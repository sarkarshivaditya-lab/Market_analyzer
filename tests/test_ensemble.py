import numpy as np
import pandas as pd

from market_analyzer.models.ensemble import IntelligenceEnsemble


def test_ensemble_target_is_forward_return():
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    frame = pd.DataFrame({
        "date": list(dates) * 2,
        "tic": ["AAA"] * 10 + ["BBB"] * 10,
        "close": list(range(100, 110)) + list(range(200, 210)),
    })
    target = IntelligenceEnsemble.target(frame, horizon=5)
    assert np.isclose(target.iloc[0], 105 / 100 - 1)
    assert pd.isna(target.iloc[5])


def test_ensemble_fits_and_predicts():
    rng = np.random.default_rng(7)
    n = 240
    frame = pd.DataFrame({
        "date": pd.date_range("2020-01-01", periods=n, freq="D"),
        "tic": ["AAA"] * n,
        "close": 100 * np.cumprod(1 + rng.normal(0.001, 0.01, n)),
        "expected_return_1d": rng.normal(0.001, 0.01, n),
        "expected_return_5d": rng.normal(0.003, 0.02, n),
        "expected_return_20d": rng.normal(0.01, 0.04, n),
        "crash_probability": rng.uniform(0, 0.3, n),
        "regime_probability": rng.uniform(0.4, 0.9, n),
        "anomaly_score": rng.uniform(0, 1, n),
    })
    frame["ensemble_target"] = frame["expected_return_5d"] * 0.5 + rng.normal(0, 0.01, n)
    model = IntelligenceEnsemble().fit(frame)
    out = model.predict(frame)
    assert len(out) > 100
    assert out["positive_return_probability"].between(0, 1).all()
