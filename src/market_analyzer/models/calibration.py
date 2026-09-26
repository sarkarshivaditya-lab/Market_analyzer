from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, average_precision_score, log_loss


@dataclass
class ProbabilityCalibrationMetrics:
    brier: float
    pr_auc: float
    log_loss: float


class ProbabilityCalibrator:
    """Fit isotonic probability calibration on strictly historical predictions."""

    def __init__(self):
        self.model = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        self.fitted = False

    def fit(self, probabilities, outcomes):
        p = np.asarray(probabilities, dtype=float)
        y = np.asarray(outcomes, dtype=float)
        mask = np.isfinite(p) & np.isfinite(y)
        if mask.sum() < 50 or np.unique(y[mask]).size < 2:
            raise ValueError("Calibration needs at least 50 observations and two outcome classes.")
        order = np.argsort(p[mask], kind="stable")
        self.model.fit(p[mask][order], y[mask][order])
        self.fitted = True
        return self

    def transform(self, probabilities):
        if not self.fitted:
            raise RuntimeError("Fit the calibrator before transforming probabilities.")
        p = np.asarray(probabilities, dtype=float)
        return np.clip(self.model.predict(p), 0.0, 1.0)

    def evaluate(self, probabilities, outcomes) -> ProbabilityCalibrationMetrics:
        p = self.transform(probabilities)
        y = np.asarray(outcomes, dtype=int)
        return ProbabilityCalibrationMetrics(
            brier=float(brier_score_loss(y, p)),
            pr_auc=float(average_precision_score(y, p)),
            log_loss=float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6))),
        )
