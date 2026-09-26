from __future__ import annotations
import pandas as pd

def risk_adjusted_weights(signals,max_weight=.35):
    d=signals.copy()
    d["raw_weight"]=d["decision_score"].clip(lower=0)*d["confidence"].clip(0,1)*(1-d["crash_probability"].clip(0,1))
    total=d["raw_weight"].sum()
    d["target_weight"]=(d["raw_weight"]/total if total>0 else 0.0).clip(upper=max_weight)
    total=d["target_weight"].sum()
    if total>0:d["target_weight"]=d["target_weight"]/total
    return d[["date","tic","target_weight","signal","risk_state"]].sort_values(["date","tic"]).reset_index(drop=True)
