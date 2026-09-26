from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import os
import requests
import pandas as pd

@dataclass(frozen=True)
class FundamentalSnapshot:
    ticker: str
    effective_at: pd.Timestamp
    filed_at: pd.Timestamp
    source: str
    values: dict[str, float]

class FundamentalProvider(Protocol):
    def fetch(self,tickers:list[str],as_of:pd.Timestamp)->list[FundamentalSnapshot]: ...

class CsvFundamentalProvider:
    def __init__(self,path:str): self.path=path
    def fetch(self,tickers:list[str],as_of:pd.Timestamp)->list[FundamentalSnapshot]:
        frame=pd.read_csv(self.path); required={"ticker","effective_at","filed_at","source"}
        missing=required-set(frame.columns)
        if missing: raise ValueError(f"Missing fundamental columns: {sorted(missing)}")
        frame["effective_at"]=pd.to_datetime(frame["effective_at"],utc=True); frame["filed_at"]=pd.to_datetime(frame["filed_at"],utc=True)
        cutoff=pd.Timestamp(as_of)
        cutoff=cutoff.tz_localize("UTC") if cutoff.tzinfo is None else cutoff.tz_convert("UTC")
        frame=frame[(frame["ticker"].isin(tickers))&(frame["filed_at"]<=cutoff)]
        metrics=[c for c in frame.columns if c not in required]; out=[]
        for _,row in frame.sort_values("filed_at").iterrows():
            out.append(FundamentalSnapshot(str(row["ticker"]),row["effective_at"],row["filed_at"],str(row["source"]),{c:float(row[c]) for c in metrics if pd.notna(row[c])}))
        return out

class SecCompanyFactsProvider:
    """Historical SEC XBRL facts using filing dates as the information-availability boundary."""
    TAGS={"revenue":"Revenues","net_income":"NetIncomeLoss","assets":"Assets","liabilities":"Liabilities","equity":"StockholdersEquity","cash":"CashAndCashEquivalentsAtCarryingValue"}
    def __init__(self,user_agent:str|None=None):
        self.user_agent=user_agent or os.getenv("SEC_USER_AGENT")
        if not self.user_agent: raise ValueError("SEC_USER_AGENT must identify the application and contact.")
        self.session=requests.Session(); self.session.headers.update({"User-Agent":self.user_agent,"Accept-Encoding":"gzip, deflate"})
        self._tickers=None
    def _ticker_map(self):
        if self._tickers is None:
            data=self.session.get("https://www.sec.gov/files/company_tickers.json",timeout=20).json()
            self._tickers={str(v["ticker"]).upper():str(v["cik_str"]).zfill(10) for v in data.values()}
        return self._tickers
    def fetch(self,tickers:list[str],as_of:pd.Timestamp)->list[FundamentalSnapshot]:
        cutoff=pd.Timestamp(as_of); cutoff=cutoff.tz_localize("UTC") if cutoff.tzinfo is None else cutoff.tz_convert("UTC")
        out=[]
        for ticker in tickers:
            cik=self._ticker_map().get(ticker.upper())
            if not cik: continue
            facts=self.session.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",timeout=30).json().get("facts",{}).get("us-gaap",{})
            chosen={}
            filed_at=None; effective=None
            for name,tag in self.TAGS.items():
                concept=facts.get(tag)
                if not concept: continue
                units=concept.get("units",{})
                unit=next(iter(units.values()),[])
                candidates=[x for x in unit if x.get("filed") and pd.Timestamp(x["filed"],tz="UTC")<=cutoff and x.get("form") in {"10-K","10-Q"} and "end" in x]
                if not candidates: continue
                item=max(candidates,key=lambda x:(x["filed"],x["end"]))
                chosen[name]=float(item["val"]); filed_at=max(filed_at,pd.Timestamp(item["filed"],tz="UTC")) if filed_at is not None else pd.Timestamp(item["filed"],tz="UTC")
                effective=max(effective,pd.Timestamp(item["end"],tz="UTC")) if effective is not None else pd.Timestamp(item["end"],tz="UTC")
            if chosen and filed_at is not None:
                out.append(FundamentalSnapshot(ticker, effective or filed_at, filed_at, "SEC XBRL", chosen))
        return out

def merge_fundamentals_asof(market:pd.DataFrame,snapshots:list[FundamentalSnapshot])->pd.DataFrame:
    if not snapshots:return market.copy()
    rows=[]
    for s in snapshots:
        row={"tic":s.ticker,"_asof":s.filed_at}; row.update({f"fund_{k}":v for k,v in s.values.items()}); rows.append(row)
    snap=pd.DataFrame(rows).sort_values(["tic","_asof"])
    left=market.copy(); left["_asof"]=pd.to_datetime(left["date"],utc=True)
    out=pd.merge_asof(left.sort_values(["tic","_asof"]),snap,on="_asof",by="tic",direction="backward")
    return out.drop(columns="_asof").sort_values(["date","tic"]).reset_index(drop=True)
