import pandas as pd
from market_analyzer.data.context import MarketContextData
from market_analyzer.data.universe import UniverseConfig
from market_analyzer.features.context import enrich_context

def test_context_merge_preserves_market_rows():
    market=pd.DataFrame({"date":["2024-01-02","2024-01-03"],"tic":["AAA","AAA"],"close":[100.,101.]})
    context=pd.DataFrame({"date":pd.to_datetime(["2024-01-01","2024-01-03"]),"breadth_pct_positive_1d":[.5,.75]})
    out=MarketContextData.merge_asof(market,context)
    assert len(out)==len(market)
    assert out.loc[0,"breadth_pct_positive_1d"]==.5
    assert out.loc[1,"breadth_pct_positive_1d"]==.75

def test_context_features_use_past_history():
    frame=pd.DataFrame({"date":pd.date_range("2024-01-01",periods=70,freq="D"),"tic":["AAA"]*70,"close":range(100,170),"macro_vix":[20+i*.1 for i in range(70)],"spy_return_20d_context":[.01]*70,"return_20d":[.03]*70,"volatility_20d":[.02]*70,"spy_volatility_20d_context":[.015]*70})
    out=enrich_context(frame)
    assert "macro_vix_chg_5d" in out and "macro_vix_z_60d" in out
    assert "relative_return_20d_vs_spy" in out
    assert out.iloc[10]["macro_vix_chg_5d"]>0

def test_local_context_does_not_use_future_listings():
    sessions=pd.date_range("2024-01-01",periods=6,freq="D")
    rows=[]
    for day in sessions:
        rows.append({"date":day,"tic":"OLD","open":100.0,"high":101.0,"low":99.0,"close":100.0+(day-sessions[0]).days,"volume":100000})
    for day in sessions[3:]:
        rows.append({"date":day,"tic":"LATE","open":200.0,"high":201.0,"low":199.0,"close":200.0,"volume":100000})
    raw=pd.DataFrame(rows)
    context=MarketContextData(
        breadth_universe=["OLD","LATE"],
        sector_symbols=["OLD","LATE"],
    ).fetch(
        "2024-01-01","2024-01-06",
        market_frame=raw,
        min_history_sessions=3,
    )
    early=context[context["date"]<pd.Timestamp("2024-01-04")]
    assert not early.empty
    assert (early["breadth_pct_positive_1d"] == 0.0).all()
    late=context[context["date"]>=pd.Timestamp("2024-01-04")]
    assert not late.empty
    jan4=late.loc[late["date"].eq(pd.Timestamp("2024-01-04")),"breadth_pct_positive_1d"].iloc[0]
    assert jan4 == 1.0

def test_local_context_applies_point_in_time_liquidity_eligibility():
    sessions=pd.date_range("2024-01-01",periods=5,freq="D")
    rows=[]
    for i,day in enumerate(sessions):
        rows.append({"date":day,"tic":"LIQUID","open":100+i,"high":101+i,"low":99+i,"close":100+i,"volume":100000})
        rows.append({"date":day,"tic":"ILLIQUID","open":100-i,"high":101-i,"low":99-i,"close":100-i,"volume":1000})
    raw=pd.DataFrame(rows)
    config=UniverseConfig(
        min_history_sessions=3,
        min_coverage_ratio=0.70,
        min_median_turnover=5_000_000,
    )
    context=MarketContextData(
        breadth_universe=["LIQUID","ILLIQUID"],
        sector_symbols=["LIQUID","ILLIQUID"],
    ).fetch("2024-01-01","2024-01-06",market_frame=raw,universe_config=config)
    day3=context.loc[context["date"].eq(pd.Timestamp("2024-01-03"))].iloc[0]
    assert day3["breadth_pct_positive_1d"]==1.0
    assert day3["breadth_median_return_1d"]>0
