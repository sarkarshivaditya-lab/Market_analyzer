import pandas as pd
from market_analyzer.data.fundamentals import FundamentalSnapshot, merge_fundamentals_asof
from market_analyzer.data.news import title_sentiment

def test_fundamentals_merge_is_point_in_time():
    market = pd.DataFrame({"date":["2024-01-10"],"tic":["AAA"],"close":[10.]})
    snaps = [FundamentalSnapshot("AAA", pd.Timestamp("2024-01-01",tz="UTC"), pd.Timestamp("2024-01-15",tz="UTC"), "x", {"pe":5})]
    out = merge_fundamentals_asof(market, snaps)
    assert pd.isna(out.loc[0, "fund_pe"])

def test_news_sentiment_bounded():
    assert -1 <= title_sentiment("strong growth and profit") <= 1
