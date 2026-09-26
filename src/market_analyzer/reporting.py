"""Structured, non-generative market briefing primitives."""
from __future__ import annotations

import pandas as pd


def latest_market_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    latest_date = df["date"].max()
    cols = [
        c for c in [
            "date", "tic", "close", "volume", "return_1d",
            "volatility_20d", "volume_z_20d", "vix",
            "turbulence", "anomaly_score", "stress_flag",
        ] if c in df.columns
    ]
    return df[df["date"] == latest_date][cols].sort_values("tic").reset_index(drop=True)
