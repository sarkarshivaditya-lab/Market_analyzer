import numpy as np
import pandas as pd

from market_analyzer.models.regime import MarketRegimeModel

def _frame(n=120):
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    x = np.linspace(-1, 1, n)
    return pd.DataFrame({
        "date": dates,
        "tic": ["SPY"] * n,
        "return_1d": x + 0.02 * np.sin(np.arange(n)),
        "volatility_20d": 0.2 + 0.01 * np.cos(np.arange(n)),
        "drawdown": -0.1 * np.abs(np.sin(np.arange(n) / 10)),
        "turbulence": np.abs(np.cos(np.arange(n) / 7)),
    })

def test_regime_model_exposes_pipeline_predict():
    frame = _frame()
    model = MarketRegimeModel(n_regimes=4).fit(
        frame,
        ["return_1d", "volatility_20d", "drawdown", "turbulence"],
    )
    out = model.predict(frame)
    assert {"date", "tic", "regime", "regime_label", "regime_probability"} <= set(out.columns)
    assert len(out) > 0
    assert np.isfinite(out["regime_probability"]).all()
