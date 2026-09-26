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


class TimeGANStressTester:
    """Train TimeGAN on historical return sequences and measure synthetic downside."""

    def __init__(self, feature_dim: int, hidden_dim: int = 32, sequence_length: int = 20,
                 seed: int = 42):
        self.sequence_length = sequence_length
        self.seed = seed
        torch.manual_seed(seed)
        self.model = TimeGAN(TimeGANConfig(feature_dim=feature_dim, hidden_dim=hidden_dim))
        self.trainer = TimeGANTrainer(self.model)
        self.fitted = False

    @staticmethod
    def make_sequences(values: np.ndarray, sequence_length: int) -> torch.Tensor:
        values = np.asarray(values, dtype=np.float32)
        if len(values) < sequence_length:
            raise ValueError("Not enough observations for TimeGAN sequences.")
        return torch.tensor(
            np.stack([values[i:i + sequence_length] for i in range(len(values) - sequence_length + 1)])
        )

    def fit(self, values: np.ndarray, epochs: int = 5, batch_size: int = 32) -> "TimeGANStressTester":
        sequences = self.make_sequences(values, self.sequence_length)
        loader = DataLoader(TensorDataset(sequences), batch_size=min(batch_size, len(sequences)), shuffle=True)
        self.trainer.fit(loader, epochs=epochs)
        self.fitted = True
        return self

    def sample(self, paths: int = 500) -> np.ndarray:
        if not self.fitted:
            raise RuntimeError("Fit the TimeGAN stress model before sampling.")
        return self.trainer.sample(paths, self.sequence_length).numpy()

    def evaluate(self, paths: int = 500) -> StressReport:
        samples = self.sample(paths)
        total_returns = np.prod(1.0 + samples, axis=1) - 1.0
        wealth = np.cumprod(1.0 + samples, axis=1)
        drawdowns = wealth / np.maximum.accumulate(wealth, axis=1) - 1.0
        return StressReport(
            synthetic_paths=len(samples),
            horizon=samples.shape[1],
            mean_return=float(np.mean(total_returns)),
            worst_mean_drawdown=float(np.min(np.mean(drawdowns, axis=0))),
            p05_return=float(np.quantile(total_returns, 0.05)),
            p01_return=float(np.quantile(total_returns, 0.01)),
        )
