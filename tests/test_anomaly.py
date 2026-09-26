import numpy as np
import pandas as pd

from market_analyzer.models.anomaly import MarketAnomalyDetector


def test_anomaly_detector_pipeline_interface():
    dates = pd.date_range("2020-01-01", periods=80, freq="D")
    frame = pd.DataFrame({
        "date": dates,
        "tic": ["AAA"] * len(dates),
        "return_1d": np.zeros(len(dates)),
        "volume_z_20d": np.zeros(len(dates)),
        "volatility_20d": np.ones(len(dates)) * 0.01,
        "turbulence": np.zeros(len(dates)),
    })
    model = MarketAnomalyDetector().fit(frame, ["return_1d", "volume_z_20d", "volatility_20d", "turbulence"])
    scored = model.score(frame)
    assert {"date", "tic", "anomaly_score", "stress_flag"}.issubset(scored.columns)
    assert len(scored) == len(frame)
