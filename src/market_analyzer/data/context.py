"""Cross-sectional market context built from point-in-time market availability."""
from __future__ import annotations
import pandas as pd
from market_analyzer.data.yahoo import YahooMarketData

DEFAULT_BREADTH_UNIVERSE=["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ITC","LT","BHARTIARTL","AXISBANK"]

class MarketContextData:
    def __init__(self,breadth_universe=None,sector_symbols=None):
        self.breadth_universe=breadth_universe or DEFAULT_BREADTH_UNIVERSE
        self.sector_symbols=sector_symbols or self.breadth_universe
    def fetch(self,start,end=None,market_frame=None,min_history_sessions=0):
        end=end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
        if market_frame is None:
            raw=YahooMarketData(start,end,sorted(set(self.breadth_universe))).fetch()
        else:
            raw=market_frame.copy()
            raw["date"]=pd.to_datetime(raw["date"])
            raw=raw[(raw["date"]>=pd.Timestamp(start)) & (raw["date"]<pd.Timestamp(end))].copy()
        raw["date"]=pd.to_datetime(raw["date"])
        raw["tic"]=raw["tic"].astype("string").str.strip().str.upper()
        raw["close"]=pd.to_numeric(raw["close"],errors="coerce")
        raw=raw.dropna(subset=["date","tic","close"])
        if min_history_sessions>0:
            raw=raw.sort_values(["tic","date"]).copy()
            raw["history_sessions"]=raw.groupby("tic").cumcount()+1
            raw=raw[raw["history_sessions"]>=int(min_history_sessions)].copy()
        prices=raw.pivot_table(index="date",columns="tic",values="close",aggfunc="last").sort_index()
        r1=prices.pct_change(); r5=prices.pct_change(5)
        out=pd.DataFrame(index=prices.index)
        out["breadth_pct_positive_1d"]=(r1>0).mean(axis=1)
        out["breadth_pct_positive_5d"]=(r5>0).mean(axis=1)
        out["breadth_median_return_1d"]=r1.median(axis=1)
        out["breadth_median_return_5d"]=r5.median(axis=1)
        out["market_return_dispersion_1d"]=r1.std(axis=1)
        out["market_return_dispersion_5d"]=r5.std(axis=1)
        out["market_cross_sectional_range_1d"]=r1.max(axis=1)-r1.min(axis=1)
        sectors=prices.reindex(columns=[x for x in self.sector_symbols if x in prices.columns])
        sr=sectors.pct_change(20)
        out["sector_leader_return_20d"]=sr.max(axis=1)
        out["sector_laggard_return_20d"]=sr.min(axis=1)
        out["sector_dispersion_20d"]=sr.std(axis=1)
        benchmark=self.breadth_universe[0] if self.breadth_universe else None
        if benchmark in prices:
            out["spy_return_20d_context"]=prices[benchmark].pct_change(20)
            out["spy_volatility_20d_context"]=r1[benchmark].rolling(20,min_periods=10).std()
        out.index.name="date"
        return out.reset_index()
    @staticmethod
    def merge_asof(market,context):
        left=market.copy(); right=context.copy()
        left["date"]=pd.to_datetime(left["date"]); right["date"]=pd.to_datetime(right["date"])
        out=pd.merge_asof(left.sort_values("date"),right.sort_values("date"),on="date",direction="backward")
        out["date"]=out["date"].dt.strftime("%Y-%m-%d")
        return out.sort_values(["date","tic"]).reset_index(drop=True)
