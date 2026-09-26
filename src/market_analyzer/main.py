from __future__ import annotations

import pandas as pd

from market_analyzer.data.market import MarketData
from market_analyzer.data.macro import MacroData
from market_analyzer.data.context import MarketContextData
from market_analyzer.features.context import enrich_context
from market_analyzer.features.engineering import FeatureEngineer
from market_analyzer.models.anomaly import MarketAnomalyDetector
from market_analyzer.models.crash import CrashRiskModel
from market_analyzer.models.multihorizon import MultiHorizonForecaster
from market_analyzer.models.regime import MarketRegimeModel
from market_analyzer.decisions.signals import build_investment_signals
from market_analyzer.risk.portfolio import risk_adjusted_weights
from market_analyzer.reporting import build_market_brief
from market_analyzer.training.walk_forward import split_frame, walk_forward_windows

FEATURES=[
"macd","rsi_30","boll_ub","boll_lb","close_30_sma","close_60_sma",
"return_1d","return_5d","return_20d","volatility_20d","volatility_60d",
"volume_z_20d","drawdown_60d","turbulence",
"macro_vix","macro_tnx","macro_dx_y_nyb","macro_gc_f","macro_cl_f",
"macro_vix_chg_5d","macro_vix_z_60d","macro_tnx_chg_20d",
"macro_dx_y_nyb_chg_5d","macro_gc_f_chg_5d","macro_cl_f_chg_5d",
"breadth_pct_positive_1d","breadth_pct_positive_5d","breadth_median_return_1d",
"breadth_median_return_5d","market_return_dispersion_1d","market_return_dispersion_5d",
"market_cross_sectional_range_1d","sector_leader_return_20d","sector_laggard_return_20d",
"sector_dispersion_20d","spy_return_20d_context","spy_volatility_20d_context",
"relative_return_20d_vs_spy","relative_volatility_vs_spy",
]

def run(symbols=None,start="2015-01-01",end=None,horizons=(1,5,20),min_train_days=756,test_days=21):
    symbols=symbols or ["SPY","QQQ","TLT","GLD"]
    market=MarketData(symbols).fetch(start,end)
    MarketData.validate(market)
    macro=MacroData().fetch(start,end)
    features=MacroData.merge_asof(market,macro)
    context=MarketContextData().fetch(start,end)
    features=MarketContextData.merge_asof(features,context)
    features=enrich_context(features)
    features=FeatureEngineer(include_vix=False,include_turbulence=True).transform(features)
    usable=[c for c in FEATURES if c in features.columns]
    dates=pd.to_datetime(features["date"])
    windows=list(walk_forward_windows(dates,min_train_days=min_train_days,test_days=test_days,horizon_days=max(horizons)))
    if not windows:
        raise ValueError("Not enough history for the requested walk-forward configuration.")
    oos_parts=[]
    for window in windows:
        train,test=split_frame(features,window)
        forecaster=MultiHorizonForecaster(horizons=horizons).fit(train,usable,train_end=window.train_end)
        pred=forecaster.predict(test)
        pred["window_test_start"]=window.test_start
        pred["window_test_end"]=window.test_end
        oos_parts.append(pred)
    forecasts=pd.concat(oos_parts,ignore_index=True).drop_duplicates(["date","tic"])
    latest_train_end=windows[-1].train_end
    train=features[dates<=latest_train_end].copy()
    primary=MultiHorizonForecaster(horizons=(5,)).fit(train,usable,train_end=latest_train_end)
    primary_forecast=primary.predict(features).rename(columns={"expected_return_5d":"expected_return"})
    crash=CrashRiskModel(horizon=20,drawdown_threshold=-.10).fit(train,usable,train_end=latest_train_end)
    regime=MarketRegimeModel().fit(train,["return_1d","return_5d","volatility_20d","drawdown_60d"])
    anomaly=MarketAnomalyDetector().fit(train,["return_1d","return_5d","volatility_20d","volume_z_20d","drawdown_60d","turbulence"])
    crash_out=crash.predict(features)
    regime_out=regime.predict(features)
    anomaly_out=anomaly.score(features)
    signals=build_investment_signals(primary_forecast,crash_out,regime_out,anomaly_out)
    portfolio=risk_adjusted_weights(signals)
    return {"features":features,"walk_forward_forecasts":forecasts,"signals":signals,"portfolio":portfolio,"brief":build_market_brief(signals,portfolio),"walk_forward_windows":windows}

if __name__=="__main__":
    result=run()
    print(result["brief"])
    print(result["portfolio"].to_string(index=False))
