from __future__ import annotations
import pandas as pd
from market_analyzer.data.market import MarketData
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
from market_analyzer.decisions.signals import build_investment_signals
from market_analyzer.risk.optimizer import PortfolioOptimizer
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
"relative_volatility_vs_spy"]

def run(symbols=None,start="2015-01-01",end=None,horizons=(1,5,20),min_train_days=756,test_days=21,fundamental_snapshots=None,news_items=None):
    symbols=symbols or ["SPY","QQQ","TLT","GLD"]
    market=MarketData(symbols).fetch(start,end); MarketData.validate(market)
    macro=MacroData().fetch(start,end)
    features=MacroData.merge_asof(market,macro)
    context=MarketContextData().fetch(start,end)
    features=MarketContextData.merge_asof(features,context)
    features=enrich_context(features)
    if fundamental_snapshots: features=merge_fundamentals_asof(features,fundamental_snapshots)
    if news_items: features=features.merge(aggregate_news(news_items),left_on=["date","tic"],right_on=["date","tic"],how="left")
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
        pred["window_test_start"]=window.test_start; pred["window_test_end"]=window.test_end
        oos_parts.append(pred)
    forecasts=pd.concat(oos_parts,ignore_index=True).drop_duplicates(["date","tic"])

    history=forecasts.merge(features,on=["date","tic"],how="left")
    history["ensemble_target"]=IntelligenceEnsemble.target(history,5)
    meta_features=IntelligenceEnsemble.feature_columns(history)
    history=history.dropna(subset=["ensemble_target"])
    if len(history)<250: raise ValueError("Insufficient out-of-sample history for ensemble training.")
    history=history.sort_values("date").reset_index(drop=True)
    split=max(100,int(len(history)*0.8))
    meta_train=history.iloc[:split].copy(); calibration_frame=history.iloc[split:].copy()
    calibrator_model=IntelligenceEnsemble().fit(meta_train,meta_features)
    calibration_pred=calibrator_model.predict(calibration_frame)
    calibration_frame=calibration_frame.merge(calibration_pred,on=["date","tic"],how="left")
    calibrator=ProbabilityCalibrator().fit(
        calibration_frame["positive_return_probability"],
        (calibration_frame["ensemble_target"]>0).astype(int)
    )
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
    risk_frame["positive_return_probability"]=calibrator.transform(risk_frame["positive_return_probability"].fillna(.5))
    risk_frame["ensemble_confidence"]=(risk_frame["positive_return_probability"]-.5).abs()*2
    decision_frame=ensemble_out.merge(risk_frame[["date","tic","crash_probability","regime_probability","anomaly_score"]],on=["date","tic"],how="left")
    signals=build_investment_signals(decision_frame,decision_frame[["date","tic","crash_probability"]],decision_frame[["date","tic","regime_probability"]],decision_frame[["date","tic","anomaly_score"]])
    latest=signals.sort_values("date").groupby("tic",as_index=False).tail(1).set_index("tic")
    returns=market.pivot(index="date",columns="tic",values="close").pct_change().dropna()
    expected=latest["ensemble_expected_return"].reindex(returns.columns).fillna(0.0)
    portfolio=PortfolioOptimizer().optimize(expected,returns)
    portfolio=portfolio.rename("target_weight").reset_index()
    return {"features":features,"walk_forward_forecasts":forecasts,"ensemble_history":history,"signals":signals,"portfolio":portfolio,"brief":build_market_brief(signals,portfolio),"walk_forward_windows":windows}

if __name__=="__main__":
    result=run()
    print(result["brief"])
    print(result["portfolio"].to_string(index=False))
