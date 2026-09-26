"""Chronological sequence construction with no future-data leakage."""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_sequences(
    df: pd.DataFrame,
    features: list[str],
    lookback: int = 60,
    target: str = "return_1d",
    horizon: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    values_x: list[np.ndarray] = []
    values_y: list[float] = []

    for ticker, group in df.sort_values(["tic", "date"]).groupby("tic"):
        group = group.dropna(subset=features + [target]).reset_index(drop=True)
        x = group[features].to_numpy(dtype=np.float32)
        y = group[target].to_numpy(dtype=np.float32)
        for end in range(lookback, len(group) - horizon + 1):
            values_x.append(x[end - lookback:end])
            values_y.append(float(y[end + horizon - 1]))

    if not values_x:
        raise ValueError("Not enough observations to create sequences.")
    return np.stack(values_x), np.asarray(values_y, dtype=np.float32)


def chronological_split(
    x: np.ndarray,
    y: np.ndarray,
    train: float = 0.7,
    validation: float = 0.15,
) -> tuple[np.ndarray, ...]:
    if not 0 < train < 1 or not 0 < validation < 1 or train + validation >= 1:
        raise ValueError("Invalid split fractions.")
    n = len(x)
    i = int(n * train)
    j = int(n * (train + validation))
    return x[:i], y[:i], x[i:j], y[i:j], x[j:], y[j:]
