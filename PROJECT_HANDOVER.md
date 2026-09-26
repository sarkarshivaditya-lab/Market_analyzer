# Market Analyzer — Project Handover

## Purpose of this file

This file is the persistent handover for the next development session. Before changing the model, data pipeline, or dashboard, read this file and re-audit the live repository state.

## Current repository

Repository: sarkarshivaditya-lab/Market_analyzer
Default branch: main
Latest audited commit: 45b0763e770e9b51ab01f99d561a50554eaf2f50
Latest commit message: document Zerodha authentication and market data

The repository is an AI-driven Indian-market financial intelligence and portfolio-decision platform. It currently contains market ingestion, technical/context features, multi-horizon forecasting, crash-risk classification, regime detection, anomaly scoring, a stacked ensemble, probability calibration, portfolio optimization, backtesting, TimeGAN stress testing, FastAPI dashboard, paper trading, and guarded Zerodha execution scaffolding.

## Three active goals

### Goal 1 — Maximize useful data and retrain

Obtain and integrate as much relevant historical market information as is realistically available, prioritizing Indian equities and data that can legally/practically be obtained at zero or low cost.

Priority:
1. Build a durable local historical market-data store instead of repeatedly relying on transient API downloads.
2. Add NSE official daily Bhavcopy/CM-UDiFF data as an Indian-source pipeline.
3. Keep Yahoo as a historical backfill/development source and compare sources rather than blindly merging them.
4. Expand the equity universe substantially beyond the current six-stock default and make universe selection configurable.
5. Add Indian-market context where possible: NIFTY 50, India VIX, sector indices, breadth/advance-decline, INR, rates, crude, gold, and other relevant macro/context series.
6. Improve fundamentals for Indian companies. The current SEC provider is US-centric and is not a production source for NSE names; CSV/provider interfaces should remain available for point-in-time Indian fundamentals.
7. Historical news must use timestamped archives. The current RSS provider is intended for live context and must not be treated as historical training evidence.
8. Preserve timestamps and information-availability boundaries to prevent look-ahead leakage.
9. Profile missingness, survivorship bias, corporate actions, symbol changes, delistings, and duplicate data before training.
10. Train/retrain models on the expanded dataset and record dataset version, date range, universe, feature set, model configuration, and evaluation results.

Do not equate more rows with better data. Data quality, survivorship bias, timestamp correctness, and point-in-time availability are first-class requirements.

### Goal 2 — Refine the algorithm from evidence

Do not tune parameters arbitrarily. Use expanded data and out-of-sample results to identify failure modes and make targeted changes.

Current known refinement targets:
- The ensemble is only partially walk-forward/nested. Base-model predictions are generated chronologically, but the meta-model/calibration process should be audited for strict nested out-of-sample evaluation.
- The current backtest is score-weighted and uses simple transaction costs/slippage. It is not yet a realistic market-impact/liquidity simulator.
- The optimizer and backtest paths need to be checked so reported backtest performance corresponds to the actual portfolio construction logic, not merely a signal-weighted proxy.
- Confidence is currently derived from classifier probability distance from 0.5. Treat it as model conviction, not automatically as calibrated probability quality.
- Calibration must be evaluated out-of-sample and must not contaminate training or model selection.
- The anomaly detector is deterministic robust-z/turbulence scoring despite the class name suggesting a learned detector. Preserve this distinction in documentation.
- Regime detection is a GMM and should be evaluated for stability across time rather than assuming the four clusters are intrinsically meaningful.
- Crash labels and their horizon/threshold need empirical class-balance and precision/recall analysis.
- Feature importance/ablation analysis should be added so the model can be simplified or strengthened based on evidence.
- Hyperparameter selection must use chronological validation, never random shuffling across time.
- Compare against simple baselines: buy-and-hold, equal weight, momentum, volatility scaling, and/or other transparent strategies as appropriate.
- Track performance across market regimes and time periods, not only one aggregate Sharpe/CAGR.
- Monitor turnover and costs. The previous backtest showed very high turnover, so this is an important algorithmic issue rather than a cosmetic metric.
- TimeGAN is a stress/scenario generator, not predictive evidence. Validate whether generated distributions are plausible before using its outputs operationally.

Target outcome: a model that is empirically better understood and more robust, not merely a model with a higher in-sample score.

### Goal 3 — Replace the table-first dashboard with trader-grade graphics

Mentor requirement: “traders need graphs.”

The dashboard should evolve from a reporting page into a visual market workstation.

Core graphical components:
1. Candlestick/price chart per selected stock.
2. Technical overlays such as moving averages, Bollinger bands, and model-relevant indicators.
3. Buy/neutral/sell or overweight/underweight signal markers directly on price charts.
4. Model expected-return/confidence/crash-risk panels.
5. Market-regime visualization over time.
6. Portfolio allocation visualization.
7. Equity curve versus NIFTY 50 benchmark.
8. Drawdown chart.
9. Rolling Sharpe/volatility/performance.
10. Turnover and transaction-cost visualization.
11. TimeGAN stress distribution/scenario visualization when equity exposure exists.
12. Paper-trading equity/position visualization.

Use graphs to answer trader questions immediately: what is happening, where is the signal, how strong is it, what is the risk, what is the portfolio doing, and how has the strategy behaved historically.

The existing API/state architecture can be retained, but the presentation layer should no longer be primarily HTML tables.

## Current architecture

Data:
- data/yahoo.py — Yahoo Finance ingestion and NSE .NS normalization.
- data/market.py — tradable market-data validation.
- data/macro.py — exogenous macro series.
- data/context.py — breadth/cross-sectional context.
- data/fundamentals.py — point-in-time snapshot protocol, CSV provider, SEC XBRL provider, derived fundamental features.
- data/news.py — RSS ingestion and simple sentiment/rolling features.
- data/zerodha.py — optional read-only Kite Connect market data.

Features:
- features/engineering.py — technical indicators, returns, volatility, volume z-score, drawdown, turbulence.
- features/context.py — macro and relative-context features.

Models:
- Multi-horizon return forecasting.
- CrashRiskModel.
- MarketRegimeModel.
- MarketAnomalyDetector.
- IntelligenceEnsemble.
- ProbabilityCalibrator.
- TimeGAN.

Decision/risk:
- decisions/signals.py — ensemble/risk-adjusted decision score and portfolio gate.
- risk/optimizer.py — long-only covariance-aware SLSQP optimizer with cash support.

Research:
- backtest/engine.py — signal backtest and basic performance metrics.
- backtest/research.py — equity metrics, benchmark comparison, rolling and fold reports.

Execution:
- execution/broker.py — PaperBroker, ZerodhaBroker, AlpacaBroker, ExecutionPolicy, ExecutionEngine.
- execution/paper.py — persistent paper-trading session.
- execution/zerodha_auth.py — Kite login/token exchange.
- scripts/kite_login.py — interactive authentication helper.

Dashboard:
- dashboard/app.py — FastAPI app with JSON state and server-rendered HTML.

## Data/provider status

Yahoo is currently the practical free development source.

Zerodha/Kite integration exists but paid Kite Connect market-data access is not being assumed. Market-data selection is controlled by MARKET_ANALYZER_MARKET_DATA_PROVIDER. Live broker execution is separately gated.

NSE official daily CM-UDiFF Bhavcopy is the next important free Indian-market data integration. Use it for ongoing local accumulation and source cross-checking. Do not claim that this provides a free full historical archive or free real-time feed.

## Important known technical debt

1. The package is configured with setuptools package discovery under src/. In the local Python 3.14 environment, normal editable imports previously failed even though the package was installed; PYTHONPATH=src and uvicorn --app-dir src were working workarounds. Do not silently assume the local packaging issue is resolved.
2. data/context.py and features/context.py retain stale “spy” feature names even though the primary universe is Indian. Rename them carefully while preserving compatibility where needed.
3. The default breadth universe is only ten stocks and the default tradable universe is six stocks. This is inadequate for serious cross-sectional modeling.
4. Macro defaults are predominantly US/global instruments (^VIX, ^TNX, DXY, gold, crude). Indian-specific context is missing.
5. SEC XBRL fundamentals are not an appropriate direct historical fundamental source for NSE companies.
6. RSS title sentiment is a simple keyword scorer, not a strong financial NLP model.
7. The dashboard still renders market signals as a table and portfolio information as mostly tables/bars. It is not yet a trader-oriented graphical interface.
8. Existing dashboard regression tests still contain legacy SPY test fixtures even though the product has migrated to NSE/NIFTY.
9. backtest/research.py still defaults to SPY in benchmark helper signatures. Indian product code should use NIFTY50/NSEI semantics.
10. ExecutionEngine uses fixed configured capital when converting target weights into quantities. Before any real execution work, this must be reconciled with actual account equity and broker position state.
11. ZerodhaBroker should not be enabled for live trading merely because the market-data provider is set to Zerodha.
12. The optimizer allows cash but needs continued testing around feasibility, zero-exposure states, and expected-return/risk unit consistency.
13. TimeGAN training is computationally expensive and currently intended for stress testing. Do not allow it to dominate the project before data/model validation is solid.
14. The project has a large dependency surface. Keep tests fast and isolate network-dependent tests with mocks.

## Safety and research rules

- No credentials in source control.
- No live execution by default.
- Preserve explicit live-trading confirmation gate.
- Never use future information in features, labels, calibration, model selection, or backtests.
- Historical news/fundamentals must respect publication/filing availability time.
- Do not report backtest performance as evidence of future returns.
- Keep paper trading separate from real execution.
- Every material model change should have a regression test and an out-of-sample comparison.

## Baseline from the previous session

Known test baseline: 64 tests passing after the latest local test run.

The latest observed model run produced all-neutral signals across the six-stock NSE universe and a 100% cash portfolio because the system had no positive decision scores meeting allocation conditions. That state is not automatically a bug; it should be investigated against the expanded data and model calibration rather than forced into equity exposure.

A previous backtest showed approximately:
- Strategy CAGR: 54.6%
- Volatility: 17.5%
- Sharpe: 2.58
- Sortino: 3.85
- Max drawdown: -15.6%
- Very high turnover: ~1431
- NIFTY50 benchmark CAGR: ~9.2%

These figures are historical development outputs only and must be revalidated after the data/model pipeline is expanded.

## Next-session execution order

1. Re-audit the current repository before editing anything.
2. Establish the actual current test/CI baseline.
3. Implement the local data layer and NSE daily Bhavcopy ingestion.
4. Expand the Indian universe and historical dataset.
5. Run data-quality and leakage audits.
6. Retrain the current model stack on the expanded data.
7. Produce a model diagnostic report and identify the highest-impact algorithmic weaknesses.
8. Refine the algorithm one evidence-backed change at a time.
9. Re-run strict chronological/out-of-sample backtests after each material change.
10. Redesign the dashboard around charts and trader workflows.
11. Add dashboard regression tests for the graphical data/API contracts.
12. Keep paper trading as the operational validation layer.
13. Only revisit broker execution after data, model, backtest, and dashboard layers are stable.

The next assistant should not jump directly into parameter tuning or UI work without first completing step 1 and recording the audit findings.
