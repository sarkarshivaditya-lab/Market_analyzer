import pandas as pd
from market_analyzer.data.fundamentals import FundamentalSnapshot,merge_fundamentals_asof

def test_fundamental_filing_boundary():
    market=pd.DataFrame({"date":["2024-01-10","2024-01-20"],"tic":["AAA","AAA"],"close":[10.,11.]})
    s=[FundamentalSnapshot("AAA",pd.Timestamp("2024-01-01",tz="UTC"),pd.Timestamp("2024-01-15",tz="UTC"),"x",{"revenue":100})]
    out=merge_fundamentals_asof(market,s)
    assert pd.isna(out.loc[0,"fund_revenue"]) and out.loc[1,"fund_revenue"]==100
