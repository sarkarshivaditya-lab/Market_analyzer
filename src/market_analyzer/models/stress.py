from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from market_analyzer.models.timegan import TimeGAN, TimeGANConfig, TimeGANTrainer


@dataclass
class StressReport:
    synthetic_paths: int
    horizon: int
    mean_return: float
    worst_mean_drawdown: float
    p05_return: float
    p01_return: float
    return_std: float
    path_dispersion: float
    collapsed: bool
    cash_only: bool = False


class TimeGANStressTester:
    """Train TimeGAN on historical multi-asset returns and measure portfolio downside."""

    def __init__(self, feature_dim: int, hidden_dim: int = 32, sequence_length: int = 20,
                 seed: int = 42):
        self.sequence_length = sequence_length
        self.seed = seed
        torch.manual_seed(seed)
        self.model = TimeGAN(TimeGANConfig(feature_dim=feature_dim, hidden_dim=hidden_dim))
        self.trainer = TimeGANTrainer(self.model)
        self.fitted = False
        self.last_total_returns = np.array([], dtype=np.float64)

    @staticmethod
    def make_sequences(values: np.ndarray, sequence_length: int) -> torch.Tensor:
        values = np.asarray(values, dtype=np.float32)
        if values.ndim != 2:
            raise ValueError("TimeGAN stress input must be a 2D date-by-asset return matrix.")
        if len(values) < sequence_length:
            raise ValueError("Not enough observations for TimeGAN sequences.")
        return torch.tensor(
            np.stack([values[i:i + sequence_length] for i in range(len(values) - sequence_length + 1)])
        )

    def fit(self, values: np.ndarray, epochs: int = 5, batch_size: int = 128) -> "TimeGANStressTester":
        sequences = self.make_sequences(values, self.sequence_length)
        loader = DataLoader(
            TensorDataset(sequences),
            batch_size=min(batch_size, len(sequences)),
            shuffle=True,
        )
        self.trainer.fit(loader, epochs=epochs)
        self.fitted = True
        return self

    def sample(self, paths: int = 250) -> np.ndarray:
        if not self.fitted:
            raise RuntimeError("Fit the TimeGAN stress model before sampling.")
        return self.trainer.sample(paths, self.sequence_length).numpy()

    def evaluate(self, paths: int = 250, weights: np.ndarray | None = None) -> StressReport:
        samples = np.clip(self.sample(paths), -0.95, 0.95)
        if weights is None:
            weights = np.full(samples.shape[-1], 1.0 / samples.shape[-1])
        weights = np.asarray(weights, dtype=np.float64)
        if weights.ndim != 1 or len(weights) != samples.shape[-1]:
            raise ValueError("Stress weights must match the asset dimension.")
        total = weights.sum()
        if total <= 0:
            raise ValueError("Stress weights must have a positive sum.")
        weights = weights / total
        portfolio_returns = np.sum(samples * weights.reshape(1, 1, -1), axis=2)
        total_returns = np.prod(1.0 + portfolio_returns, axis=1) - 1.0
        self.last_total_returns = total_returns.astype(np.float64, copy=True)
        wealth = np.cumprod(1.0 + portfolio_returns, axis=1)
        drawdowns = wealth / np.maximum.accumulate(wealth, axis=1) - 1.0
        return_std=float(np.std(total_returns))
        path_dispersion=float(np.mean(np.std(portfolio_returns,axis=1)))
        collapsed=bool(return_std < 1e-4 or path_dispersion < 1e-5)
        return StressReport(
            synthetic_paths=len(samples),
            horizon=samples.shape[1],
            mean_return=float(np.mean(total_returns)),
            worst_mean_drawdown=float(np.min(np.mean(drawdowns, axis=0))),
            p05_return=float(np.quantile(total_returns, 0.05)),
            p01_return=float(np.quantile(total_returns, 0.01)),
            return_std=return_std,
            path_dispersion=path_dispersion,
            collapsed=collapsed,
        )
