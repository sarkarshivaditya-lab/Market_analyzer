from __future__ import annotations
from dataclasses import asdict
import os
import numpy as np
import pandas as pd
from market_analyzer.data.market import MarketData
from market_analyzer.data.yahoo import YahooMarketData
from market_analyzer.data.zerodha import ZerodhaMarketData
from market_analyzer.data.local import NSELocalMarketData, NSELocalMarketStore
from market_analyzer.data.universe import UniverseConfig, eligible_tickers_on
from market_analyzer.data.macro import MacroData
from market_analyzer.data.context import MarketContextData
from market_analyzer.data.fundamentals import merge_fundamentals_asof
from market_analyzer.data.news import aggregate_news
from market_analyzer.features.context import enrich_context
from market_analyzer.features.engineering import FeatureEngineer
from market_analyzer.models.anomaly import MarketAnomalyDetector
from market_analyzer.models.calibration import ProbabilityCalibrator
from market_analyzer.models.crash import CrashRiskModel
from market_analyzer.models.ensemble import IntelligenceEnsemble
from market_analyzer.models.multihorizon import MultiHorizonForecaster
from market_analyzer.models.regime import MarketRegimeModel
from market_analyzer.models.stress import TimeGANStressTester
from market_analyzer.decisions.signals import build_investment_signals, apply_portfolio_gate
from market_analyzer.risk.optimizer import PortfolioOptimizer
from market_analyzer.backtest.engine import signal_backtest, performance_metrics
from market_analyzer.backtest.research import compare_strategy_to_benchmark, rolling_forward_performance
from market_analyzer.reporting import build_market_brief
from market_analyzer.training.walk_forward import split_frame, walk_forward_windows

FEATURES=[
"macd","rsi_30","boll_ub","boll_lb","close_30_sma","close_60_sma","return_1d","return_5d","return_20d",
"volatility_20d","volatility_60d","volume_z_20d","drawdown_60d","turbulence","macro_vix","macro_tnx",
"macro_dx_y_nyb","macro_gc_f","macro_cl_f","macro_vix_chg_5d","macro_vix_z_60d","macro_tnx_chg_20d",
"macro_dx_y_nyb_chg_5d","macro_gc_f_chg_5d","macro_cl_f_chg_5d","breadth_pct_positive_1d",
"breadth_pct_positive_5d","breadth_median_return_1d","breadth_median_return_5d","market_return_dispersion_1d",
"market_return_dispersion_5d","market_cross_sectional_range_1d","sector_leader_return_20d","sector_laggard_return_20d",
"sector_dispersion_20d","spy_return_20d_context","spy_volatility_20d_context","relative_return_20d_vs_spy",
"relative_volatility_vs_spy",
"fund_revenue","fund_net_income","fund_assets","fund_liabilities","fund_equity","fund_cash",
"fund_revenue_growth","fund_net_income_growth","fund_profit_margin","fund_debt_to_assets","fund_equity_ratio","fund_cash_to_assets",
"fund_revenue_log","fund_net_income_log","fund_assets_log","fund_liabilities_log","fund_equity_log","fund_cash_log",
"news_count","news_sentiment","news_sentiment_3d","news_sentiment_7d","news_count_3d","news_count_7d"]

def load_market_data(symbols, start, end):
    provider=os.getenv("MARKET_ANALYZER_MARKET_DATA_PROVIDER","yahoo").strip().lower()
    if provider=="zerodha":
        return ZerodhaMarketData().fetch(start or "2015-01-01",end or pd.Timestamp.utcnow().strftime("%Y-%m-%d"),symbols)
    if provider=="nse_local":
        store_path=os.getenv("MARKET_ANALYZER_NSE_STORE_PATH","data/market/nse.sqlite")
        cache_dir=os.getenv("MARKET_ANALYZER_NSE_CACHE_DIR","data/raw/nse")
        return NSELocalMarketData(start or "2015-01-01",end or pd.Timestamp.utcnow().strftime("%Y-%m-%d"),symbols,store_path=store_path,cache_dir=cache_dir).fetch()
    if provider!="yahoo":
        raise ValueError("MARKET_ANALYZER_MARKET_DATA_PROVIDER must be 'yahoo', 'nse_local' or 'zerodha'")
    return MarketData(symbols).fetch(start,end)


def _resolve_symbols(symbols, start, end):
    if symbols:
        return symbols
    mode=os.getenv("MARKET_ANALYZER_UNIVERSE","default").strip().lower()
    if mode != "registry":
        return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN"]
    if os.getenv("MARKET_ANALYZER_MARKET_DATA_PROVIDER","yahoo").strip().lower() != "nse_local":
        raise ValueError("MARKET_ANALYZER_UNIVERSE=registry requires MARKET_ANALYZER_MARKET_DATA_PROVIDER=nse_local")
    store_path=os.getenv("MARKET_ANALYZER_NSE_STORE_PATH","data/market/nse.sqlite")
    store=NSELocalMarketStore(store_path)
    effective_end=end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    frame=store.load(start or "2015-01-01",effective_end)
    if frame.empty:
        raise ValueError("NSE local store has no data for the requested universe window.")
    sessions=pd.DatetimeIndex(frame["date"].unique()).sort_values()
    config=UniverseConfig(
        min_history_sessions=int(os.getenv("MARKET_ANALYZER_MIN_HISTORY_SESSIONS","756")),
        min_coverage_ratio=float(os.getenv("MARKET_ANALYZER_MIN_COVERAGE_RATIO","0.70")),
        min_median_turnover=float(os.getenv("MARKET_ANALYZER_MIN_MEDIAN_TURNOVER","10000000")),
    )
    selected=eligible_tickers_on(frame,effective_end,sessions,config)
    if not selected:
        raise ValueError("NSE universe registry produced no eligible symbols.")
    return selected


def run(symbols=None,start="2015-01-01",end=None,horizons=(1,5,20),min_train_days=756,test_days=21,fundamental_snapshots=None,news_items=None):
    symbols=_resolve_symbols(symbols,start,end)
    market=load_market_data(symbols,start,end)
    MarketData.validate(market)
    macro=MacroData().fetch(start,end)
    features=MacroData.merge_asof(market,macro)
    context=MarketContextData(breadth_universe=symbols,sector_symbols=symbols).fetch(start,end)
    features=MarketContextData.merge_asof(features,context)
    features=enrich_context(features)
    if fundamental_snapshots:
        features=merge_fundamentals_asof(features,fundamental_snapshots)
    if news_items:
        news_frame=aggregate_news(news_items)
        features=features.merge(news_frame,on=["date","tic"],how="left")
    for column in [c for c in features.columns if c.startswith("fund_") or c.startswith("news_")]:
        features[column]=pd.to_numeric(features[column],errors="coerce")
    features[["news_count","news_sentiment","news_count_3d","news_count_7d","news_sentiment_3d","news_sentiment_7d"]]=features.reindex(columns=["news_count","news_sentiment","news_count_3d","news_count_7d","news_sentiment_3d","news_sentiment_7d"]).fillna(0.0)
    features=FeatureEngineer(include_vix=False,include_turbulence=True).transform(features)
    usable=[c for c in FEATURES if c in features.columns]
    dates=pd.to_datetime(features["date"])
    windows=list(walk_forward_windows(dates,min_train_days=min_train_days,test_days=test_days,horizon_days=max(horizons)))
    if not windows: raise ValueError("Not enough history for the requested walk-forward configuration.")
    oos_parts=[]
    for window in windows:
        train,test=split_frame(features,window)
        base=MultiHorizonForecaster(horizons=horizons).fit(train,usable,train_end=window.train_end)
        pred=base.predict(test)
        pred["window_test_start"]=window.test_start
        pred["window_test_end"]=window.test_end
        oos_parts.append(pred)
    forecasts=pd.concat(oos_parts,ignore_index=True).drop_duplicates(["date","tic"])
    history=forecasts.merge(features,on=["date","tic"],how="left")
    history["ensemble_target"]=IntelligenceEnsemble.target(history,5)
    meta_features=IntelligenceEnsemble.feature_columns(history)
    history=history.dropna(subset=["ensemble_target"])
    if len(history)<250: raise ValueError("Insufficient out-of-sample history for ensemble training.")
    history=history.sort_values("date").reset_index(drop=True)
    split=max(100,int(len(history)*0.8))
    meta_train=history.iloc[:split].copy()
    calibration_frame=history.iloc[split:].copy()
    calibrator_model=IntelligenceEnsemble().fit(meta_train,meta_features)
    calibration_pred=calibrator_model.predict(calibration_frame)
    calibration_frame=calibration_frame.merge(calibration_pred,on=["date","tic"],how="left")
    calibrator=ProbabilityCalibrator().fit(calibration_frame["positive_return_probability"],(calibration_frame["ensemble_target"]>0).astype(int))
    ensemble=IntelligenceEnsemble().fit(history,meta_features)
    latest_train_end=windows[-1].train_end
    train=features[dates<=latest_train_end].copy()
    base_current=MultiHorizonForecaster(horizons=horizons).fit(train,usable,train_end=latest_train_end)
    current_base=base_current.predict(features)
    crash=CrashRiskModel(horizon=20,drawdown_threshold=-.10).fit(train,usable,train_end=latest_train_end)
    regime=MarketRegimeModel().fit(train,["return_1d","return_5d","volatility_20d","drawdown_60d"])
    anomaly=MarketAnomalyDetector().fit(train,["return_1d","return_5d","volatility_20d","volume_z_20d","drawdown_60d","turbulence"])
    risk_frame=features.merge(current_base,on=["date","tic"],how="left")
    risk_frame=risk_frame.merge(crash.predict(features),on=["date","tic"],how="left")
    risk_frame=risk_frame.merge(regime.predict(features),on=["date","tic"],how="left")
    risk_frame=risk_frame.merge(anomaly.score(features),on=["date","tic"],how="left")
    ensemble_out=ensemble.predict(risk_frame)
    risk_frame=risk_frame.merge(ensemble_out,on=["date","tic"],how="left")
    raw_probability=risk_frame["positive_return_probability"].fillna(.5)
    risk_frame["positive_return_probability"]=calibrator.transform(raw_probability)
    risk_frame["ensemble_confidence"]=(raw_probability-.5).abs()*2
    decision_frame=risk_frame[["date","tic","ensemble_expected_return","positive_return_probability","ensemble_confidence","crash_probability","regime_probability","anomaly_score","regime_label"]].copy()
    signals=build_investment_signals(decision_frame,pd.DataFrame(columns=["date","tic","crash_probability"]),pd.DataFrame(columns=["date","tic","regime_probability"]),pd.DataFrame(columns=["date","tic","anomaly_score"]))
    signals["date"]=pd.to_datetime(signals["date"])
    latest=signals.sort_values("date").groupby("tic",as_index=False).tail(1).set_index("tic")
    min_confidence=float(os.getenv("MARKET_ANALYZER_MIN_PORTFOLIO_CONFIDENCE","0.05"))
    max_crash_probability=float(os.getenv("MARKET_ANALYZER_MAX_PORTFOLIO_CRASH","0.50"))
    latest=apply_portfolio_gate(latest,min_confidence=min_confidence,max_crash_probability=max_crash_probability)
    returns=market.pivot(index="date",columns="tic",values="close").pct_change().dropna()
    eligible=latest[latest["portfolio_eligible"]].copy()
    no_positive_signal=eligible["decision_score"]<=0.0
    eligible.loc[no_positive_signal,"allocation_reason"]="NO_POSITIVE_SIGNAL"
    eligible=eligible[~no_positive_signal]
    eligible_assets=[asset for asset in eligible.index if asset in returns.columns]
    eligible_returns=returns[eligible_assets] if eligible_assets else returns.iloc[:,0:0]
    expected=eligible["decision_score"].reindex(eligible_assets).fillna(0.0)
    portfolio=PortfolioOptimizer().optimize(expected,eligible_returns,allow_cash=True)
    portfolio=portfolio.rename("target_weight").reindex(returns.columns,fill_value=0.0).reset_index()
    portfolio=portfolio.merge(latest[["signal","risk_state","confidence","portfolio_eligible","allocation_reason"]].reset_index(),on="tic",how="right").fillna({"target_weight":0.0})
    price_frame=market[["date","tic","close"]].copy()
    backtest=signal_backtest(signals,price_frame,transaction_cost_bps=5.0,slippage_bps=2.0)
    benchmark_market=YahooMarketData(start,end,["^NSEI"]).fetch()
    benchmark_prices=benchmark_market.pivot(index="date",columns="tic",values="close").rename(columns={"^NSEI":"NIFTY50"})
    price_matrix=market.pivot(index="date",columns="tic",values="close").sort_index().ffill()
    price_matrix=price_matrix.join(benchmark_prices,how="left").ffill()
    comparison=compare_strategy_to_benchmark(backtest["return"],price_matrix,benchmark="NIFTY50")
    backtest_summary={"strategy":performance_metrics(backtest),"benchmark":comparison["benchmark"],"transaction_cost_bps":5.0,"slippage_bps":2.0}
    # Build explicit chart-ready series from real model/data outputs. No synthetic UI values are created here.
    chart_market={}
    chart_source=market.copy()
    chart_source["date"]=pd.to_datetime(chart_source["date"])
    for tic,group in chart_source.groupby("tic"):
        frame=group.sort_values("date").copy()
        frame["sma20"]=frame["close"].rolling(20).mean()
        frame["sma50"]=frame["close"].rolling(50).mean()
        bb_mid=frame["close"].rolling(20).mean()
        bb_std=frame["close"].rolling(20).std()
        frame["bb_upper"]=bb_mid+2.0*bb_std
        frame["bb_lower"]=bb_mid-2.0*bb_std
        signal_cols=["date","tic","signal","expected_return","confidence","crash_probability","risk_state","regime_label","anomaly_score"]
        available=[c for c in signal_cols if c in signals.columns]
        frame=frame.merge(signals[available],on=["date","tic"],how="left")
        latest_signal_date=pd.to_datetime(signals["date"]).max()
        frame["signal_marker"]=frame["signal"].where(frame["date"].eq(latest_signal_date))
        records=frame.replace({np.nan:None}).to_dict("records")
        for record in records:
            record["date"]=pd.Timestamp(record["date"]).strftime("%Y-%m-%d")
        chart_market[str(tic)]=records
    regime_rows=[]
    regime_source=risk_frame[["date","regime_label","regime_probability"]].copy()
    regime_source["date"]=pd.to_datetime(regime_source["date"])
    for dt,group in regime_source.groupby("date"):
        labels=group["regime_label"].dropna().astype(str)
        label=labels.mode().iloc[0] if not labels.empty else "UNKNOWN"
        probability=pd.to_numeric(group["regime_probability"],errors="coerce").mean()
        regime_rows.append({"date":dt.strftime("%Y-%m-%d"),"label":label,"probability":None if pd.isna(probability) else float(probability)})
    benchmark_series=benchmark_prices["NIFTY50"].pct_change().fillna(0.0)
    benchmark_equity=(1.0+benchmark_series).cumprod()
    strategy_equity=backtest["equity"].astype(float)
    drawdown=strategy_equity/strategy_equity.cummax()-1.0
    rolling=rolling_forward_performance(backtest["return"],window=63)
    performance_frame=pd.DataFrame({
        "date":pd.to_datetime(backtest.index),
        "strategy_equity":strategy_equity.to_numpy(),
        "benchmark_equity":benchmark_equity.reindex(backtest.index).ffill().fillna(1.0).to_numpy(),
        "drawdown":drawdown.to_numpy(),
        "rolling_sharpe":rolling["rolling_sharpe"].to_numpy(),
        "rolling_volatility":rolling["rolling_volatility"].to_numpy(),
        "turnover":backtest["turnover"].to_numpy(),
        "transaction_cost":backtest["cost"].to_numpy(),
    })
    performance_records=performance_frame.replace({np.nan:None}).to_dict("records")
    for record in performance_records:
        record["date"]=pd.Timestamp(record["date"]).strftime("%Y-%m-%d")
    # Persist the dashboard-ready research state before stress/paper stages so a later optional stage cannot leave the workstation stale.
    from market_analyzer.dashboard.app import set_state
    latest_signal_records=signals[signals["date"]==signals["date"].max()].copy()
    latest_signal_records["date"]=latest_signal_records["date"].dt.strftime("%Y-%m-%d")
    set_state(
        signals=latest_signal_records.to_dict("records"),
        portfolio=portfolio.to_dict("records"),
        backtest=backtest_summary,
        stress={},
        paper={},
        market={"symbols":list(chart_market),"default_symbol":str(portfolio.iloc[0]["tic"]) if len(portfolio) else (list(chart_market)[0] if chart_market else None),"series":chart_market,"regime":regime_rows},
        performance={"series":performance_records},
    )
    stress_summary=stress_summary if "stress_summary" in locals() else {}
    stress_weights=portfolio.set_index("tic")["target_weight"].reindex(returns.columns).fillna(0.0).to_numpy()
    stress_input=returns.reindex(columns=portfolio["tic"]).fillna(0.0).to_numpy()
    if float(stress_weights.sum()) <= 0:
        from market_analyzer.models.stress import StressReport
        stress_summary=asdict(StressReport(
            synthetic_paths=0,horizon=20,mean_return=0.0,worst_mean_drawdown=0.0,
            p05_return=0.0,p01_return=0.0,return_std=0.0,path_dispersion=0.0,
            collapsed=False,cash_only=True
        ))
    else:
        stress_model=TimeGANStressTester(feature_dim=stress_input.shape[1],hidden_dim=16,sequence_length=20,seed=42)
        stress_model.fit(stress_input,epochs=5,batch_size=128)
        stress_report=stress_model.evaluate(paths=100,weights=stress_weights)
        stress_summary=asdict(stress_report)
        stress_summary["distribution"]=stress_model.last_total_returns.tolist()
    brief=build_market_brief(signals,portfolio)
    from market_analyzer.execution.paper import PaperTradingSession
    latest_prices=market.sort_values("date").groupby("tic").tail(1).set_index("tic")["close"].to_dict()
    state_file=os.getenv("MARKET_ANALYZER_PAPER_STATE_FILE","market_analyzer_paper.json")
    paper=PaperTradingSession.create(capital=100000.0,state_file=state_file)
    paper_result=paper.rebalance(portfolio[["tic","target_weight"]],latest_prices)
    set_state(signals=latest_signal_records.to_dict("records"),portfolio=portfolio.to_dict("records"),brief=brief,backtest=backtest_summary,stress=stress_summary,paper=paper_result,market={"symbols":list(chart_market),"default_symbol":str(portfolio.iloc[0]["tic"]) if len(portfolio) else (list(chart_market)[0] if chart_market else None),"series":chart_market,"regime":regime_rows},performance={"series":performance_records})
    return {"features":features,"walk_forward_forecasts":forecasts,"ensemble_history":history,"signals":signals,"portfolio":portfolio,"brief":brief,"backtest":backtest,"backtest_summary":backtest_summary,"stress":stress_summary,"walk_forward_windows":windows,"dashboard_market":chart_market,"dashboard_performance":performance_records,"dashboard_regime":regime_rows}

if __name__=="__main__":
    result=run()
    print(result["brief"])
    print(result["portfolio"].to_string(index=False))
    print(result["backtest_summary"])
    print(result["stress"])