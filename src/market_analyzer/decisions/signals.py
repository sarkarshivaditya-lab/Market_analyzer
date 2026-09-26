from __future__ import annotations
import numpy as np
import pandas as pd

def _merge_missing(out, extra):
    missing=[c for c in extra.columns if c not in out.columns or c in {"date","tic"}]
    if not missing:
        return out
    return out.merge(extra[["date","tic"]+[c for c in missing if c not in {"date","tic"}]],on=["date","tic"],how="left")

def build_investment_signals(forecast, crash, regime, anomaly):
    out=forecast.copy()
    out=_merge_missing(out,crash)
    out=_merge_missing(out,regime)
    out=_merge_missing(out,anomaly)
    if "ensemble_expected_return" in out:
        out["expected_return"]=out["ensemble_expected_return"]
        out["confidence"]=out["ensemble_confidence"]
        out["positive_return_probability"]=out["positive_return_probability"]
        out["decision_score"]=out["ensemble_expected_return"]*out["positive_return_probability"]*(1-out["crash_probability"].fillna(0))
    else:
        trend=np.tanh(out["expected_return"]*10.0)
        out["confidence"]=np.clip(.5*out.get("regime_probability",.5)+.5*(1-out["crash_probability"]),0,1)
        out["decision_score"]=trend-(1.5*out["crash_probability"]+.5*out["anomaly_score"])
    out["signal"]=np.select([out["decision_score"]>.002,out["decision_score"]<-.002],["OVERWEIGHT","UNDERWEIGHT"],default="NEUTRAL")
    out["risk_state"]=np.select([out["crash_probability"]>=.5,out["anomaly_score"]>=.7],["HIGH_CRASH_RISK","ANOMALOUS"],default="NORMAL")
    return out

def latest_signals(signals):
    d=signals.copy(); d["date"]=pd.to_datetime(d["date"])
    return d.sort_values("date").groupby("tic",as_index=False).tail(1).sort_values("tic").reset_index(drop=True)
