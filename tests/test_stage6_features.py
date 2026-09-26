import pandas as pd
import pytest

from market_analyzer.data.fundamentals import FundamentalSnapshot,enrich_fundamentals,merge_fundamentals_asof
from market_analyzer.data.news import NewsItem,aggregate_news,title_sentiment

def test_enrich_fundamentals_adds_quality_features():
    frame=pd.DataFrame({
        "date":["2024-01-01","2024-01-02"],
        "tic":["AAA","AAA"],
        "fund_revenue":[100.0,120.0],
        "fund_net_income":[10.0,18.0],
        "fund_assets":[200.0,220.0],
        "fund_liabilities":[80.0,88.0],
        "fund_equity":[120.0,132.0],
        "fund_cash":[30.0,33.0],
    })
    out=enrich_fundamentals(frame)
    assert out["fund_revenue_growth"].iloc[1]==pytest.approx(.2)
    assert out["fund_profit_margin"].iloc[1]==pytest.approx(.15)
    assert out["fund_debt_to_assets"].iloc[1]==pytest.approx(.4)
    assert "fund_revenue_log" in out

def test_fundamentals_asof_does_not_leak_and_derives_features():
    market=pd.DataFrame({"date":["2024-01-10","2024-01-20"],"tic":["AAA","AAA"],"close":[10.,11.]})
    snapshots=[FundamentalSnapshot("AAA",pd.Timestamp("2024-01-01",tz="UTC"),pd.Timestamp("2024-01-15",tz="UTC"),"x",{"revenue":100.,"net_income":10.,"assets":200.,"liabilities":80.,"equity":120.,"cash":30.})]
    out=merge_fundamentals_asof(market,snapshots)
    assert pd.isna(out.loc[0,"fund_revenue"])
    assert out.loc[1,"fund_revenue"]==100.
    assert out.loc[1,"fund_profit_margin"]==pytest.approx(.1)

def test_news_aggregation_adds_rolling_context():
    items=[
        NewsItem("AAA",pd.Timestamp("2024-01-01",tz="UTC"),"test","profit growth","u",title_sentiment("profit growth")),
        NewsItem("AAA",pd.Timestamp("2024-01-02",tz="UTC"),"test","warning loss","u",title_sentiment("warning loss")),
        NewsItem("AAA",pd.Timestamp("2024-01-08",tz="UTC"),"test","upgrade strong","u",title_sentiment("upgrade strong")),
    ]
    out=aggregate_news(items)
    row=out[(out["date"]=="2024-01-08")&(out["tic"]=="AAA")].iloc[0]
    assert row["news_count_3d"]==1
    assert row["news_count_7d"]==2
    expected=(title_sentiment("warning loss")+title_sentiment("upgrade strong"))/2
    assert row["news_sentiment_7d"]==pytest.approx(expected)

def test_title_sentiment_is_bounded():
    assert -1.0<=title_sentiment("fraud loss warning")<=1.0
    assert -1.0<=title_sentiment("record growth upgrade")<=1.0
