"""Point-in-time-safe transformations for exogenous context."""
from __future__ import annotations
import pandas as pd

def enrich_context(frame):
    out=frame.copy().sort_values(["tic","date"]).reset_index(drop=True)
    for column in [c for c in out.columns if c.startswith("macro_")]:
        series=pd.to_numeric(out[column],errors="coerce")
        out[f"{column}_chg_5d"]=out.groupby("tic")[column].transform(lambda x:x.pct_change(5))
        out[f"{column}_z_60d"]=out.groupby("tic")[column].transform(lambda x:(x-x.rolling(60,min_periods=20).mean())/(x.rolling(60,min_periods=20).std()+1e-8))
    if "macro_tnx" in out:
        out["macro_tnx_chg_20d"]=out.groupby("tic")["macro_tnx"].transform(lambda x:x.diff(20))
    if "macro_vix" in out:
        out["macro_vix_return_5d"]=out.groupby("tic")["macro_vix"].transform(lambda x:x.pct_change(5))
    if "spy_return_20d_context" in out and "return_20d" in out:
        out["relative_return_20d_vs_spy"]=out["return_20d"]-out["spy_return_20d_context"]
    if "spy_volatility_20d_context" in out and "volatility_20d" in out:
        out["relative_volatility_vs_spy"]=out["volatility_20d"]-out["spy_volatility_20d_context"]
    return out
