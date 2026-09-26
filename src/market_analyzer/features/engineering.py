"""Feature engineering inspired by established FinRL preprocessing patterns."""
from __future__ import annotations
import numpy as np
import pandas as pd
from stockstats import StockDataFrame as Sdf

DEFAULT_INDICATORS=["macd","rsi_30","boll_ub","boll_lb","close_30_sma","close_60_sma"]

class FeatureEngineer:
    def __init__(self, indicators=None, include_vix=False, include_turbulence=True):
        self.indicators=indicators or DEFAULT_INDICATORS
        self.include_vix=include_vix
        self.include_turbulence=include_turbulence

    def transform(self, df, vix=None):
        self._validate(df)
        out=self._clean(df)
        out=self._technical_indicators(out)
        out=self._returns_and_volatility(out)
        if self.include_vix and vix is not None:
            out=self._merge_vix(out,vix)
        if self.include_turbulence and out["tic"].nunique()>1:
            out=self._merge_turbulence(out)
        numeric=[c for c in out.columns if c not in {"date","tic"}]
        out[numeric]=out.groupby("tic",group_keys=False)[numeric].ffill()
        return out.sort_values(["date","tic"]).reset_index(drop=True)

    @staticmethod
    def _validate(df):
        required={"date","tic","open","high","low","close","volume"}
        missing=required.difference(df.columns)
        if missing: raise ValueError(f"Missing required columns: {sorted(missing)}")

    @staticmethod
    def _clean(df):
        out=df.copy()
        out["date"]=pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
        out=out.sort_values(["tic","date"]).drop_duplicates(["tic","date"])
        return out.reset_index(drop=True)

    def _technical_indicators(self,df):
        out=df.sort_values(["tic","date"]).copy()
        pieces=[]
        for ticker,group in out.groupby("tic",sort=False):
            sdf=Sdf.retype(group.copy())
            result=group.copy()
            for indicator in self.indicators:
                try: result[indicator]=sdf[indicator].to_numpy()
                except Exception: result[indicator]=np.nan
            pieces.append(result)
        return pd.concat(pieces,ignore_index=True).sort_values(["date","tic"]).reset_index(drop=True)

    @staticmethod
    def _returns_and_volatility(df):
        out=df.sort_values(["tic","date"]).copy()
        g=out.groupby("tic",group_keys=False)
        out["return_1d"]=g["close"].pct_change()
        out["return_5d"]=g["close"].pct_change(5)
        out["return_20d"]=g["close"].pct_change(20)
        out["volatility_20d"]=g["return_1d"].transform(lambda x:x.rolling(20,min_periods=10).std())
        out["volatility_60d"]=g["return_1d"].transform(lambda x:x.rolling(60,min_periods=20).std())
        out["volume_z_20d"]=g["volume"].transform(lambda x:(x-x.rolling(20,min_periods=10).mean())/(x.rolling(20,min_periods=10).std()+1e-8))
        out["drawdown_60d"]=g["close"].transform(lambda x:x/x.rolling(60,min_periods=20).max()-1.0)
        return out

    @staticmethod
    def _merge_vix(df,vix):
        v=vix[["date","close"]].rename(columns={"close":"vix"}).copy()
        v["date"]=pd.to_datetime(v["date"]).dt.strftime("%Y-%m-%d")
        return df.merge(v,on="date",how="left")

    @staticmethod
    def _merge_turbulence(df):
        returns=df.pivot(index="date",columns="tic",values="close").pct_change()
        dates=returns.index
        values=[]
        for i in range(len(dates)):
            if i<60: values.append(np.nan); continue
            hist=returns.iloc[max(0,i-252):i].dropna(axis=1)
            current=returns.iloc[i]
            if hist.shape[0]<30 or hist.shape[1]==0: values.append(np.nan); continue
            cols=hist.columns.intersection(current.dropna().index)
            if len(cols)==0: values.append(np.nan); continue
            diff=(current[cols]-hist[cols].mean()).to_numpy(float).reshape(1,-1)
            cov=hist[cols].cov().to_numpy()
            values.append(max(float(diff@np.linalg.pinv(cov)@diff.T),0.0))
        return df.merge(pd.DataFrame({"date":dates,"turbulence":values}),on="date",how="left")
