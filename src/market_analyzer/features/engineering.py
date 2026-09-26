"""Financial feature engineering based on FinRL's preprocessing approach."""
from __future__ import annotations

import numpy as np
import pandas as pd
from stockstats import StockDataFrame as Sdf


DEFAULT_INDICATORS = [
    "macd",
    "rsi_30",
    "boll_ub",
    "boll_lb",
    "close_30_sma",
    "close_60_sma",
]


class FeatureEngineer:
    def __init__(
        self,
        indicators: list[str] | None = None,
        include_vix: bool = False,
        include_turbulence: bool = True,
    ):
        self.indicators = indicators or DEFAULT_INDICATORS
        self.include_vix = include_vix
        self.include_turbulence = include_turbulence

    def transform(self, df: pd.DataFrame, vix: pd.DataFrame | None = None) -> pd.DataFrame:
        self._validate(df)
        out = self._clean(df)

        if self.indicators:
            out = self._technical_indicators(out)

        out = self._returns_and_volatility(out)

        if self.include_vix and vix is not None:
            out = self._merge_vix(out, vix)

        if self.include_turbulence and out["tic"].nunique() > 1:
            out = self._merge_turbulence(out)

        return out.ffill().bfill()

    @staticmethod
    def _validate(df: pd.DataFrame) -> None:
        required = {"date", "tic", "open", "high", "low", "close", "volume"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

    @staticmethod
    def _clean(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["date"] = out["date"].astype(str)
        out = out.sort_values(["date", "tic"]).reset_index(drop=True)
        complete = out.pivot(index="date", columns="tic", values="close").dropna(axis=1).columns
        return out[out["tic"].isin(complete)].reset_index(drop=True)

    def _technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.sort_values(["tic", "date"]).copy()
        sdf = Sdf.retype(out.copy())
        result = out.copy()
        for indicator in self.indicators:
            parts: list[pd.DataFrame] = []
            for ticker in out["tic"].unique():
                sub = sdf[sdf.tic == ticker].copy()
                try:
                    values = pd.DataFrame({indicator: sub[indicator]})
                    values["tic"] = ticker
                    values["date"] = out.loc[out["tic"] == ticker, "date"].to_numpy()
                    parts.append(values)
                except Exception:
                    continue
            if parts:
                indicator_df = pd.concat(parts, ignore_index=True)
                result = result.merge(
                    indicator_df,
                    on=["tic", "date"],
                    how="left",
                )
        return result.sort_values(["date", "tic"]).reset_index(drop=True)

    @staticmethod
    def _returns_and_volatility(df: pd.DataFrame) -> pd.DataFrame:
        out = df.sort_values(["tic", "date"]).copy()
        grouped = out.groupby("tic", group_keys=False)
        out["return_1d"] = grouped["close"].pct_change(1)
        out["return_5d"] = grouped["close"].pct_change(5)
        out["return_20d"] = grouped["close"].pct_change(20)
        out["volatility_20d"] = grouped["return_1d"].transform(lambda x: x.rolling(20).std())
        out["volume_z_20d"] = grouped["volume"].transform(
            lambda x: (x - x.rolling(20).mean()) / (x.rolling(20).std() + 1e-8)
        )
        return out.sort_values(["date", "tic"]).reset_index(drop=True)

    @staticmethod
    def _merge_vix(df: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
        v = vix[["date", "close"]].rename(columns={"close": "vix"})
        v["date"] = v["date"].astype(str)
        return df.merge(v, on="date", how="left")

    @staticmethod
    def _merge_turbulence(df: pd.DataFrame) -> pd.DataFrame:
        pivot = df.pivot(index="date", columns="tic", values="close").pct_change()
        dates = pivot.index
        values = [0.0] * min(252, len(dates))
        for i in range(252, len(dates)):
            current = pivot.iloc[i]
            history = pivot.iloc[i - 252:i].dropna(axis=1)
            if history.empty:
                values.append(0.0)
                continue
            current = current[history.columns]
            mean = history.mean(axis=0)
            cov = history.cov()
            diff = (current - mean).to_numpy(dtype=float).reshape(1, -1)
            value = float(diff @ np.linalg.pinv(cov.to_numpy()) @ diff.T)
            values.append(max(value, 0.0))
        turbulence = pd.DataFrame({"date": dates, "turbulence": values})
        return df.merge(turbulence, on="date", how="left")
