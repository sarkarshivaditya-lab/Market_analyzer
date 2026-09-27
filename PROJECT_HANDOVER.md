# Market Analyzer — Project Handover

## Purpose of this file

This file is the persistent handover for the next development session. Before changing the model, data pipeline, or dashboard, read this file and re-audit the live repository state.

## Current repository

Repository: sarkarshivaditya-lab/Market_analyzer
Default branch: main
Latest audited commit: 9c635645c2cdf21adf30300c3e34666a9bc37bcd (separate adjusted NSE research store builder)
Latest commit message: add separate adjusted NSE research store builder

The repository is an AI-driven Indian-market financial intelligence and portfolio-decision platform. It currently contains market ingestion, technical/context features, multi-horizon forecasting, crash-risk classification, regime detection, anomaly scoring, a stacked ensemble, probability calibration, portfolio optimization, backtesting, TimeGAN stress testing, FastAPI dashboard, paper trading, and guarded Zerodha execution scaffolding.

## Current-session audit and Goal 3 milestone

Audit date: 2026-09-27.

The live main branch was re-audited before dashboard work. The handover's recorded latest audited commit (45b0763e...) was stale; the actual starting HEAD was 8d6106503a70e03216b26514a3db356d6ee95293, which already included the NSE CM-UDiFF provider and its tests. src/market_analyzer/main.py also exists and is the current orchestrator; the earlier concern that main.py was difficult to retrieve is no longer applicable.

The dashboard milestone is COMPLETE and has been runtime-verified locally. /api/state remains unchanged as the primary endpoint, with backward-compatible state persistence and additional market/performance fields. The dashboard uses browser-native canvas/SVG-free rendering with no paid chart dependency. It provides selected NSE price/candlestick views with SMA20/SMA50/Bollinger overlays, latest signal markers, model expected-return/confidence/crash/anomaly panels, market-regime timeline, portfolio allocation, strategy-versus-NIFTY50 equity curve, drawdown, rolling risk, turnover, transaction cost, TimeGAN stress distribution, and paper-account/equity/position visualization. The user visually verified the populated NSE workstation in the browser on 2026-09-27.

Historical model outputs are not presented as an out-of-sample trading history. Price-chart signal markers are restricted to the latest model decision because the existing current-model inference path can generate retrospective in-sample outputs across historical dates. The backtest charts continue to use the existing backtest engine outputs.

During runtime verification, three serialization/compatibility defects in the new dashboard path were fixed: signal date type mismatch during market-series merge, pandas Timestamp objects in the first dashboard state write, and the same Timestamp issue in the final state write. The final successful local run completed the full pipeline and populated the browser dashboard. Uvicorn must be run separately from the pipeline because the dashboard only serves persisted state.

Paper equity history is now persisted in the paper broker state from this point forward. Existing paper state files without an equity_history field remain compatible.

The available GitHub connector does not expose a local shell or a push-triggered workflow-run listing for this repository. The repository's test workflow exists at .github/workflows/tests.yml. A previous local baseline was 92 passed; the final dashboard runtime fixes in commits 6f1cbbf, 88a0b5c, and a8ef465 have not yet been followed by a fresh pytest run. Do not record a new test total until pytest is run locally or CI is verified.

## Three active goals

### Goal 1 — Maximize useful data and retrain

Current Goal 1 progress: the local NSE store now contains broad CM history through 2026-09-25, a point-in-time universe registry has been added, and corporate-action history has now been acquired from the NSE corporate-actions API for all 1,133 currently eligible symbols. A non-destructive quality audit now also flags large close-to-close price discontinuities that may indicate corporate actions or symbol/data issues. The registry applies minimum history, coverage, median turnover, and explicit symbol-screen rules, while eligible_tickers_on() never reads observations after its as-of date. MARKET_ANALYZER_UNIVERSE=registry is opt-in and requires MARKET_ANALYZER_MARKET_DATA_PROVIDER=nse_local. The registry is intentionally not presented as a perfect security master: the local schema preserves only rows already filtered to NSE EQ series, so instrument classification beyond that is an explicit screening layer. Next: fix the corporate-action reconciliation report so matched jumps expose the actual action/purpose/factor, classify the 349 exact jump/action matches, tighten the parser so ratio-only split descriptions remain review-only unless an explicit face-value change is present, build a separate adjusted research series without mutating raw SQLite, re-run the discontinuity audit, then complete eligible-universe continuity/survivorship/symbol-change/leakage checks before retraining.

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
7. The trader-oriented graphical dashboard is now implemented and runtime-verified. Remaining dashboard work is hardening/regression coverage, not redesign.
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

## Baseline from the current session

The local test baseline before the final dashboard runtime fixes was 92 passed. No fresh pytest result has been recorded after commits 6f1cbbf, 88a0b5c, and a8ef465.

The final local pipeline run completed successfully on the six-stock NSE default universe using MARKET_ANALYZER_MARKET_DATA_PROVIDER=nse_local. Data date: 2026-09-25. The model produced UNDERWEIGHT for RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK and SBIN except TCS, which was NEUTRAL. The optimizer produced a 100% cash / 0% equity target because no positive decision scores met the allocation conditions. Do not force exposure; investigate this behavior with expanded data and calibration diagnostics.

Latest successful six-stock development backtest from that run:
- Strategy CAGR: 53.83%
- Volatility: 19.03%
- Sharpe: 2.36
- Sortino: 3.08
- Max drawdown: -16.27%
- Total turnover: ~1537.65
- Total cost: ~1.0764
- NIFTY50 benchmark CAGR: 9.22%

These are historical development outputs only and must be revalidated after the data/model pipeline is expanded. High turnover remains a known research issue.

Paper state still contains legacy QQQ/SPY/TLT positions in the persistent paper file. This is separate from the NSE dashboard and must be cleaned/reset before treating paper-trading state as an Indian-market operational baseline.

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


## Goal 1 continuation — 2026-09-27
- Corporate-action reconciliation was corrected so exact price-jump matches are retained even when the action is review-only; the report now distinguishes any exact action match from an automatically adjustable match and prints adjustment-type classification.
- The corporate-action parser was tightened: ratio-only split descriptions are review-only unless explicit face/share-value text establishes a price-adjusting split.
- Added a non-destructive adjusted research-series builder. Corporate actions are applied only to a separate research copy; raw NSE SQLite remains the source of truth and is never mutated.
- Optimized cumulative historical adjustment factors by ticker so the ~5M-row NSE store is not scanned once per corporate action.
- Added scripts/build_adjusted_nse_store.py to materialize a separate data/market/nse_adjusted.sqlite research store from the raw store plus the acquired NSE corporate-action CSV.
- Added regression coverage for ratio-only split safety, cumulative adjustments, and raw-frame immutability.
- Next immediate task: run the corrected reconciliation against the full 1,133-symbol universe, inspect the exact-match classification counts, build the adjusted research store, then audit continuity/gaps on the 1,133 eligible universe rather than the full long tail.
- No expanded model retraining should occur until those checks complete.


## Goal 1 audit status — 2026-09-26
- Local NSE store audit: 4,914,061 rows across 3,796 tickers; zero duplicate rows, missing values, invalid OHLC rows, nonpositive prices, or negative-volume rows.
- Universe screen: 3,796 symbols examined; 1,133 currently eligible under the configured history/coverage/liquidity/symbol filters.
- Raw-price continuity remains unresolved: 2,180 close-jump candidates at the 1.5x threshold.
- Large candidates include extreme discontinuities such as KAUSHALYA, WINSOME, DIACABS, SUMEETINDS and ARIHANT; these must be reconciled against corporate actions before expanded retraining.
- 1,702 tickers have at least one missing expected session within their observed active span; this statistic includes the long tail and must be re-evaluated on the eligible universe.
- NSE documentation identifies corporate-action reports containing symbol, series, ex-date and corporate-action description, and notes that Bhavcopy prices are unadjusted while certain NSE reports provide corporate-action-adjusted values.
- Added conservative corporate-action parser/adjuster supporting unambiguous bonus and split factors; ambiguous actions such as rights/demergers remain review-only. The current parser still needs tightening because ratio-only split text is too permissive.
- Added scripts/reconcile_corporate_actions.py with resumable NSE corporate-action API acquisition. Full acquisition completed for 1,133 eligible symbols: 925 freshly fetched, 208 cached, 0 failed, 15,651 rows, ex-date range 1996-12-04 to 2026-10-06.
- Reconciliation currently reports 15,651 parsed actions, 548 automatically adjustable actions, and 349 price-jump candidates with exact ticker/ex-date matches. The report currently does not expose the matched action details correctly; all 349 must be inspected/classified before any adjustment.
- Raw SQLite market data has not been mutated by corporate-action processing. This must remain the invariant.
- Added --universe and --summary-only support to the NSE audit CLI.
- Expanded retraining remains blocked pending corporate-action reconciliation, adjusted research-series construction, eligible-universe continuity/survivorship checks, and leakage review.

## Goal 1 point-in-time universe audit — 2026-09-27
- Adjusted research store audit passed structural checks: 4,914,061 rows, 3,796 tickers, zero duplicates/missing values/invalid OHLC/nonpositive prices/negative volume/zero volume.
- On the 1,133 full-period eligible symbols, the adjusted store contains 2,488,774 rows and 237 price-jump candidates at the existing 1.5x threshold.
- Eligible-universe continuity currently shows 327 tickers with at least one missing expected session. This is not yet a failure: gaps must be classified by duration, listing/suspension lifecycle, and whether they materially affect model windows.
- Added scripts/audit_point_in_time_universe.py to quantify quarterly point-in-time eligible-universe counts using eligible_tickers_on(), which filters data at each as-of date and therefore does not use future rows.
- Added a regression test proving the point-in-time eligibility calculation does not admit a newly listed ticker before it has sufficient history.
- Immediate next execution: run scripts/audit_point_in_time_universe.py against data/market/nse_adjusted.sqlite, then use its quarterly counts and gap/jump summaries to determine survivorship and continuity risk.
- Expanded retraining remains blocked until the point-in-time universe and remaining discontinuities are understood.
