import numpy as np
from market_analyzer.models.calibration import ProbabilityCalibrator

def test_probability_calibration_stays_bounded():
    rng = np.random.default_rng(4)
    p = rng.uniform(0.01, 0.99, 120)
    y = (p + rng.normal(0, 0.15, 120) > 0.5).astype(int)
    c = ProbabilityCalibrator().fit(p, y)
    out = c.transform([0.0, 0.2, 0.8, 1.0])
    assert np.all((out >= 0) & (out <= 1))
