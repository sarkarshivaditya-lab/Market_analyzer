"""Mechanical leakage and time-boundary audit helpers."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import pandas as pd

@dataclass(frozen=True)
class AuditFinding:
    check: str
    status: str
    detail: str
    def to_dict(self): return asdict(self)

def _ordered(frame, date_col, ticker_col):
    data=frame.copy()
    data[date_col]=pd.to_datetime(data[date_col])
    return data.sort_values([ticker_col,date_col])

def audit_target_end_dates(frame,horizon,date_col="date",ticker_col="tic"):
    ordered=_ordered(frame,date_col,ticker_col)
    future=ordered.groupby(ticker_col)[date_col].shift(-horizon)
    valid=future.notna()
    if not valid.any(): return AuditFinding("target_end_dates","FAIL","No observations have a complete forward horizon.")
    return AuditFinding("target_end_dates","PASS",f"Checked {int(valid.sum())} observations with complete {horizon}-session forward horizons.")

def audit_train_target_boundary(source_frame,train_frame,train_end,horizon,date_col="date",ticker_col="tic"):
    source=_ordered(source_frame,date_col,ticker_col)
    train=_ordered(train_frame,date_col,ticker_col)
    train_end=pd.Timestamp(train_end)
    if train.empty: return AuditFinding("train_target_boundary","FAIL","Training subset is empty.")
    if pd.to_datetime(train[date_col]).max()>train_end: return AuditFinding("train_target_boundary","FAIL","Training subset contains rows after train_end.")
    source_dates=source[[ticker_col,date_col]].copy()
    source_dates["_future_date"]=source_dates.groupby(ticker_col)[date_col].shift(-horizon)
    checked=train[[ticker_col,date_col]].drop_duplicates().merge(source_dates,on=[ticker_col,date_col],how="left")
    bad=checked["_future_date"].notna()&(checked["_future_date"]>train_end)
    if bad.any(): return AuditFinding("train_target_boundary","FAIL",f"{int(bad.sum())} training rows have a {horizon}-session target after train_end={train_end.date()}.")
    return AuditFinding("train_target_boundary","PASS",f"Training subset is target-safe through {train_end.date()}.")

def audit_walk_forward_boundaries(windows,horizon):
    failures=[]; previous_test_end=None
    for i,window in enumerate(windows):
        if window.train_end>=window.test_start: failures.append(f"window {i}: train_end >= test_start")
        if previous_test_end is not None and window.test_start<=previous_test_end: failures.append(f"window {i}: test periods overlap or move backward")
        previous_test_end=window.test_end
    if failures: return AuditFinding("walk_forward_boundaries","FAIL","; ".join(failures))
    return AuditFinding("walk_forward_boundaries","PASS",f"Validated {len(windows)} chronological windows; train/test periods do not overlap.")

def audit_asof_availability(frame,availability_col,decision_col="date"):
    if availability_col not in frame.columns: return AuditFinding("asof_availability","UNKNOWN",f"Column {availability_col!r} is absent; historical information availability cannot be mechanically proven.")
    available=pd.to_datetime(frame[availability_col],errors="coerce"); decision=pd.to_datetime(frame[decision_col],errors="coerce")
    bad=available.notna()&decision.notna()&(available>decision)
    if bad.any(): return AuditFinding("asof_availability","FAIL",f"{int(bad.sum())} rows have information availability after the decision date.")
    return AuditFinding("asof_availability","PASS","All supplied availability timestamps are on or before the decision date.")

def audit_point_in_time_membership(frame,universe_by_date,date_col="date",ticker_col="tic"):
    data=frame.copy(); data[date_col]=pd.to_datetime(data[date_col]).dt.normalize()
    dates=sorted(pd.Timestamp(d).normalize() for d in universe_by_date); bad=checked=0
    for row in data[[date_col,ticker_col]].itertuples(index=False):
        candidates=[d for d in dates if d<=row[0]]
        if not candidates: continue
        checked+=1
        if row[1] not in universe_by_date[max(candidates)]: bad+=1
    if bad: return AuditFinding("point_in_time_membership","FAIL",f"{bad} of {checked} checked rows are outside the supplied as-of universe.")
    return AuditFinding("point_in_time_membership","PASS",f"All {checked} checked rows are members of the supplied point-in-time universe.")

def audit_fold_isolation(train,test,date_col="date"):
    train_dates=pd.to_datetime(train[date_col]); test_dates=pd.to_datetime(test[date_col])
    if train_dates.empty or test_dates.empty: return AuditFinding("fold_isolation","FAIL","Training or test fold is empty.")
    if train_dates.max()>=test_dates.min(): return AuditFinding("fold_isolation","FAIL","Training data reaches or exceeds the first test date.")
    return AuditFinding("fold_isolation","PASS",f"train_max={train_dates.max().date()} < test_min={test_dates.min().date()}")

def audit_feature_availability_columns(frame,required_timestamp_pairs):
    findings=[]
    for feature,availability in required_timestamp_pairs.items():
        if feature not in frame.columns: findings.append(AuditFinding(feature,"UNKNOWN",f"Feature {feature!r} is absent."))
        elif availability not in frame.columns: findings.append(AuditFinding(feature,"UNKNOWN",f"No availability timestamp {availability!r}; causal availability cannot be proven."))
        else:
            finding=audit_asof_availability(frame,availability); findings.append(AuditFinding(feature,finding.status,finding.detail))
    return findings
