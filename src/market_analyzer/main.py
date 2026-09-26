from __future__ import annotations
import pandas as pd
from market_analyzer.data.yahoo import YahooFinanceData
from market_analyzer.features.engineering import FeatureEngineer
from market_analyzer.models.anomaly import MarketAnomalyDetector
from market_analyzer.models.crash import CrashRiskModel
from market_analyzer.models.forecasting import ReturnForecaster
from market_analyzer.models.regime import MarketRegimeModel
from market_analyzer.decisions.signals import build_investment_signals
from market_analyzer.risk.portfolio import risk_adjusted_weights
from market_analyzer.reporting import build_market_brief

FEATURES=["macd","rsi_30","boll_ub","boll_lb","close_30_sma","close_60_sma","return_1d","return_5d","return_20d","volatility_20d","volatility_60d","volume_z_20d","drawdown_60d","turbulence"]

def run(symbols=None, start="2015-01-01", horizon=5):
    symbols=symbols or ["SPY","QQQ","TLT","GLD"]
    loader=YahooFinanceData()
    prices=loader.download(symbols,start=start)
    features=FeatureEngineer(include_vix=True,include_turbulence=True).transform(prices,loader.download(["^VIX"],start=start).assign(tic="^VIX"))
    usable=[c for c in FEATURES if c in features.columns]
    train_end=pd.to_datetime(features["date"]).quantile(0.75)
    forecaster=ReturnForecaster(horizon=horizon).fit(features,usable,train_end)
    crash=CrashRiskModel(horizon=20,drawdown_threshold=-0.10).fit(features,usable,train_end)
    regime=MarketRegimeModel().fit(features,["return_1d","return_5d","volatility_20d","drawdown_60d"])
    anomaly=MarketAnomalyDetector().fit(features,["return_1d","return_5d","volatility_20d","volume_z_20d","drawdown_60d","turbulence"])
    forecast=forecaster.predict(features)
    crash_out=crash.predict(features)
    regime_out=regime.predict(features)
    anomaly_out=anomaly.score(features)
    signals=build_investment_signals(forecast,crash_out,regime_out,anomaly_out)
    portfolio=risk_adjusted_weights(signals)
    brief=build_market_brief(signals,portfolio)
    return {"features":features,"signals":signals,"portfolio":portfolio,"brief":brief}

if __name__=="__main__":
    result=run()
    print(result["brief"])
    print(result["portfolio"].to_string(index=False))
