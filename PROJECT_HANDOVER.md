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

### Corporate-action adjustment milestone
- Corporate-action parser was corrected for composite bonus + face-value split events. When both are explicitly described in the same event, the parser combines the bonus and split price factors rather than treating the components independently.
- Ratio-only split descriptions remain review-only unless explicit face/share-value text establishes an actual face-value change. This prevents false historical price adjustments.
- Added `filter_corporate_actions_to_window()` and applied it in `scripts/build_adjusted_nse_store.py`. Corporate actions outside the requested research window are excluded, preventing an event after the as-of/end date from back-adjusting earlier observations in a finite research dataset.
- The adjusted research series remains non-destructive. `data/market/nse.sqlite` is never mutated; the separate `data/market/nse_adjusted.sqlite` store is the research artifact.
- Corporate-action regression suite is now green: `11 passed in 0.17s`.
- Latest adjusted-store rebuild verified:
  - raw_rows=4,914,061
  - parsed_actions=12,530
  - adjustable_actions=445
  - adjusted_rows_written=4,914,061
  - adjusted_tickers=3,796
  - raw_store_unchanged=True
- The lower parsed/adjustable counts relative to the full API acquisition are expected because the research window is 2015-01-01 through 2026-09-27; actions outside that window are deliberately excluded.
- The corrected continuity classification on the adjusted store reports:
  - gap_runs=808
  - tickers_with_gaps=327
  - total_missing_sessions=40,747
  - residual price-jump candidates=224
  - exact action/date matches=11
  - exact matches with an automatically adjustable factor=0
  - all 11 exact matches are review-only events
- The 11 exact review-only matches are:
  - ADANIENT 2015-06-03 — Scheme Of Arrangement — -82.77%
  - SINTEX 2017-05-25 — Scheme Of Arrangement — -75.17%
  - ABFRL 2025-05-22 — Demerger — -66.59%
  - ARVIND 2018-11-28 — Demerger — -65.09%
  - VEDL 2026-04-30 — Demerger — -64.90%
  - IDFC 2015-10-01 — Demerger — -57.21%
  - TATACHEM 2020-03-04 — Demerger — -56.53%
  - HERITGFOOD 2023-01-20 — Rights 1:1 @ Premium Rs 0/- — -46.84%
  - PEL 2022-08-30 — Demerger — -44.79%
  - SIEMENS 2025-04-07 — Demerger — -42.93%
  - IDEA 2019-03-29 — Rights 87:38 @ Premium Of Rs 2.50 Per Share — -37.07%
- Therefore the current adjustment engine should NOT be broadened merely to eliminate every residual jump. Review-only actions such as demergers, schemes of arrangement, and rights issues may represent genuine economic/share-structure events requiring separate treatment rather than simple price-factor normalization.
- The largest unmatched residuals include VERTOZ +621.66%, MCLEODRUSS +566.67%, OPTIEMUS +261.79%, OLECTRA +234.25%, MEDICO +225.56%, SPTL +188.89%, OPTIEMUS +182.08%, GLOBUSSPR +148.92%, TEJASNET +141.70%, and TTML +131.81%.
- Several large residuals occur immediately after long missing-data runs, so continuity and corporate-action context must be classified together. Do not infer an adjustment factor from the observed price jump alone.
- Current point-in-time universe audit remains an explicit prerequisite for retraining. The full-period static 1,133-symbol registry is useful for screening but must not become the historical training universe without as-of filtering.
- Expanded model retraining remains blocked.

### Residual-jump diagnostic classifier
- Added `classify_jump_context()` to `src/market_analyzer/data/quality.py`.
- The classifier is diagnostic only. It never creates or applies a price-adjustment factor.
- Each residual jump is classified using:
  - exact corporate-action date,
  - nearest corporate action within a bounded calendar window (default 5 days),
  - number of expected sessions missing between the previous observed ticker date and the jump date.
- Current classification buckets are `exact_action`, `near_action`, `post_gap`, `near_action_and_post_gap`, and `unexplained`.
- Added unit tests in `tests/test_quality.py` covering all four diagnostic paths and their key invariants.
- Updated `scripts/classify_nse_continuity.py` to print the residual-context distribution and top contextualized jumps.
- Next local validation command:
  `PYTHONPATH=src pytest tests/test_quality.py tests/test_corporate_actions.py -q`
- If tests pass, rerun `scripts/classify_nse_continuity.py` against the adjusted store and use the resulting category counts to decide which residuals require external corporate-action/source investigation.
- Do not automatically add adjustment factors from the new classifications.

### Residual-jump classification result — 2026-09-27
- Local validation of the residual-context classifier completed successfully enough to produce the full classification report.
- Residual candidates remain 224.
- Classification distribution:
  - exact_action: 11
  - near_action_and_post_gap: 1
  - post_gap: 126
  - unexplained: 86
- Therefore 137/224 residuals have some corporate-action relationship in the current diagnostic sense, but only 12 are action-adjacent and only 11 are exact-date matches. The 126 post-gap cases should not be interpreted as corporate actions merely because a large jump occurs when trading resumes.
- The largest residuals are overwhelmingly post-gap events: VERTOZ +621.66% after 110 missing sessions, MCLEODRUSS +566.67% after 139 missing sessions, OPTIEMUS +261.79% after 114 missing sessions, OLECTRA +234.25% after 122 missing sessions, and MEDICO +225.56% after 116 missing sessions.
- The 86 unexplained cases are more important for direct data-integrity investigation because they occur without a preceding missing-session run and without a nearby corporate action under the current five-day diagnostic window. Examples include MAJESCO -98.76%, ICICITECH -90.16%, AEGISCHEM -90.11%, IEX -90.09%, ITDCEM -90.06%, JETAIRWAYS +89.88%, and INFIBEAM -89.82%.
- No new price-adjustment factors should be introduced from this report. The diagnostic establishes where investigation is needed; it does not establish the correct economic adjustment.
- Next priority is to separate post-gap resumption effects from true data/vendor discontinuities, then investigate the 86 same-session unexplained jumps using source/corporate-action/symbol-history evidence.
- After residual continuity is sufficiently understood, complete the point-in-time universe audit and leakage review before any expanded retraining.

### Immediate next execution
1. Build a residual-jump classifier that joins the 224 residuals against:
   - exact-date corporate actions,
   - nearby corporate actions within a bounded date window,
   - the end of preceding continuity gaps,
   - the start of following continuity gaps,
   - symbol-level listing/history boundaries.
2. Classify residuals into evidence-backed buckets such as exact corporate action, near-action, post-gap continuity issue, overlap/ambiguous, or unexplained.
3. Do not automatically adjust any new class until the evidence supports a deterministic factor.
4. Re-run the point-in-time universe audit and explicitly measure whether the remaining gaps can contaminate feature lookback/label horizons.
5. Audit survivorship and symbol-history handling, then perform the leakage audit.
6. Only after those checks pass, retrain the model stack on the expanded Indian dataset.



### Point-in-time universe audit result — 2026-09-27
- The local point-in-time audit was rerun against `data/market/nse_adjusted.sqlite` through 2026-09-27 (market data currently ends 2026-09-25).
- `full_period_eligible=1,133` under the current registry rules, but this static full-period set must not be used as the historical training universe.
- Quarterly eligible counts are 0 from 2015-01-01 through 2018-01-01, then 541 at 2018-04-01 and rise gradually to 1,104 by 2026-07-01. This is a registry limitation, not evidence that no NSE securities existed before 2018.
- Full-period eligible continuity remains imperfect: 327/1,133 eligible tickers have at least one missing expected session, with 40,747 missing sessions total; median 75, p90 297.8, p95 384.7 missing sessions per affected ticker.
- Retraining remains blocked until the historical-universe policy for 2015-2018 and gap/lookback/label handling are explicit.

### Leakage audit — repository inspection, 2026-09-27
- The repository has chronological walk-forward splitting with a purge equal to the maximum prediction horizon. This is directionally correct for time-series evaluation.
- The base return forecaster and crash model restrict training rows so forward target dates also fall on or before the training cutoff, protecting the train boundary from forward-label leakage.
- Core technical features are predominantly causal rolling calculations. However, features are engineered over the complete frame before walk-forward fitting, so every external/as-of feature source still needs an explicit information-availability audit.
- A material evaluation weakness exists in `main.py`: walk-forward base predictions are accumulated into `history`, then the ensemble is fitted once on the entire accumulated OOS history. This is not strict nested walk-forward meta-model evaluation. The calibration stage is likewise a single chronological holdout rather than nested fold-by-fold calibration.
- The historical meta-model frame also does not contain the full crash/regime/anomaly prediction columns even though the ensemble feature selector accepts them when available; this is a feature-availability/design inconsistency to resolve during the evaluation refactor.
- The calibrator is fitted on a later chronological slice than its meta-model training data, which is preferable to fitting on the same observations, but production calibration still needs an untouched later OOS evaluation or nested calibration protocol.
- `research/sequence.py` has chronological splitting but operates after sequence construction and does not itself enforce ticker/date boundary isolation; its callers require separate auditing.
- No random-shuffle cross-validation was found in the inspected core training path. The main remaining leakage risks are nested ensemble/calibration evaluation, point-in-time external data availability, and security-history/cross-sectional handling.
- Next implementation target: a dedicated leakage audit/report that mechanically checks target end dates, walk-forward boundaries, as-of joins, universe eligibility, and nested ensemble/calibration boundaries. Retraining stays blocked until this audit is clean.


### Leakage audit implementation update — 2026-09-27
- Mechanical leakage audit is now clean:
  - target_end_dates: PASS
  - walk_forward_boundaries: PASS across 21 chronological windows
  - train_target_boundary: PASS with explicit horizon purge
  - fold_isolation: PASS
  - asof_availability synthetic check: PASS
- Targeted regression suite is 13/13 passing:
  `tests/test_leakage_audit.py tests/test_model_leakage.py tests/test_walk_forward.py`.
- The mechanical audit initially exposed that its own script was testing an intentionally unpurged training slice. The script was corrected to construct the target-safe training subset before auditing the boundary.
- Production-path inspection then confirmed the substantive nested-evaluation defect in `main.py`: the ensemble was previously fit once on the complete accumulated OOS history, and calibration used a single late holdout.
- `main.py` has now been changed to strict nested meta-model evaluation:
  - each walk-forward test fold is predicted by an ensemble trained only on earlier OOS base predictions;
  - the resulting nested ensemble predictions are retained as `ensemble_oos_predictions`;
  - the final production ensemble is fit on the full historical OOS base-prediction history only after nested evaluation is generated.
- Calibration is now fit only on the nested OOS ensemble predictions, rather than on predictions from observations used to fit the final ensemble.
- Commit: `26100ae38e8ff1974df11d97bd5b3874298441e3` — `enforce nested ensemble and calibration evaluation`.
- This refactor has not yet been locally runtime-verified. Before proceeding, run the targeted tests plus the full application path.
- Remaining leakage/data-integrity blockers:
  1. point-in-time universe enforcement during each historical walk-forward fold;
  2. cross-sectional context must not be constructed from a current/survivor-only universe for historical folds;
  3. external fundamentals/news must carry and enforce information-availability timestamps;
  4. regime/anomaly signals need explicit fold-fit semantics if used as historical meta-features;
  5. residual unexplained price jumps and post-gap continuity effects still require investigation.
- Do not retrain the expanded model stack yet.


### Nested research-backtest correction — 2026-09-27
- Runtime verification after commit `ce8f4da000b5d234318b91e389af4b2ca844c370` succeeded:
  - targeted leakage/model/walk-forward tests: 13 passed in 1.59s
  - `PYTHONPATH=src python -m market_analyzer.main` completed successfully.
- The successful runtime exposed a further evaluation defect in `main.py`: `signal_backtest()` was consuming `signals) generated by the final production ensemble fitted on all historical OOS base-prediction history. Therefore the reported historical backtest remained contaminated by retrospective in-sample meta-model predictions.
- Corrected in commit `7e88ea685e140a084d61a16b48ec1093208b1ff4`:
  - construct `oos_signals` from `nested_ensemble_oos`;
  - use `oos_signals` as the sole input to `signal_backtest()`;
  - retain `signals` for the latest/current production decision path.
- Added regression test `tests/test_backtest_oos.py` in commit `9ea5adb56533243dba71cc87ebf7a3f6db07d760` to lock the supplied-signal date/position behavior of the backtest engine.
- Historical ensemble inputs had another evaluation inconsistency: `IntelligenceEnsemble.feature_columns()` permits crash/regime/anomaly predictions, but the existing historical `history` frame did not contain fold-specific versions of those models; they were generated from a latest/final fit over the full feature history. These columns are now excluded from historical meta-feature training in commit `d5822132e228c6584884f857e5aebd34b00d9373` rather than treated as OOS.
- The latest/current production path still includes crash/regime/anomaly outputs for live decision support. This distinction is intentional until fold-specific risk-model predictions are implemented.
- The OOS backtest has not yet been locally rerun after commits `7e88ea6` and `d5822132`. Next validation:
  1. `git pull origin main`
  2. `PYTHONPATH=src pytest tests/test_backtest_oos.py tests/test_leakage_audit.py tests/test_model_leakage.py tests/test_walk_forward.py -q`
  3. `PYTHONPATH=src python -m market_analyzer.main`
- Do not compare the new backtest CAGR/Sharpe with the old 53.83%/2.36 figures as an apples-to-apples model improvement. The research methodology changed to remove retrospective signal contamination.
- Expanded retraining remains blocked pending point-in-time universe enforcement, fold-specific cross-sectional context, external information-availability timestamps, and residual jump/symbol-history investigation.


### Backtest date-contract fix — 2026-09-27
- The new OOS backtest regression initially failed because `signal_backtest()` preserved string-valued date indices when callers supplied string dates.
- Corrected in commit `cd0d1015ffe44d08a96ac4076624945e29f027a6`: `signal_backtest()` now normalizes both price and signal dates with `pd.to_datetime()` at its boundary.
- This is an engine-level data-contract hardening change; the regression test remains strict about Timestamp-index access.
- Re-run the same targeted suite before the full application runtime.


### OOS backtest regression expectation correction — 2026-09-27
- The OOS backtest regression then failed on its expected first-day return.
- Cause: `signal_backtest()` correctly charges 7 bps total transaction cost/slippage for the initial 100% position change, producing `-0.0007) rather than zero. The following day earns 10% gross and pays 7 bps on the exit, producing `0.0993).
- Test corrected in commit `b13c8c1f1e3bda54932b651e268c6d04fad04baf`.
- No production backtest logic was changed for this failure.


### OOS backtest risk-feature leakage fix — 2026-09-27
- Main runtime failed because `history` correctly no longer contains `crash_probability`, `regime_probability`, `anomaly_score`, or `regime_label` after the historical meta-feature leakage fix.
- The previous OOS backtest construction still attempted to merge those columns from `history`; this was stale and invalid.
- Removed that merge. Historical research signals now use only nested OOS ensemble outputs.
- `build_investment_signals()` now supplies neutral defaults for missing risk outputs in ensemble-only mode: crash probability 0, regime probability 0.5, anomaly score 0, regime label UNKNOWN.
- This prevents final/latest risk-model predictions from contaminating the historical OOS backtest.
- Commits: `7064250` and `0a93cf4`.


### Benchmark comparison bug found — 2026-09-27
- Latest leakage-clean runtime completed, but benchmark metrics were all zero.
- Root cause: `market` dates are string-valued while Yahoo NIFTY50 benchmark dates were timestamps; the join therefore produced no overlapping benchmark dates and `compare_strategy_to_benchmark()` converted the resulting missing benchmark returns to zeros.
- Fixed by normalizing both market and benchmark dates to pandas datetime before the join in `main.py`.
- Commit: `5d419635af8a9283dcbd65f3bbd1de4736734e46`.
- The observed OOS strategy metrics from that run (CAGR ~0.03%, Sharpe ~0.08, max DD ~-46.2%) should not yet be treated as the final evidence set until the corrected benchmark comparison is rerun and the remaining data/universe issues are resolved.


### First corrected leakage-clean OOS baseline — 2026-09-27
- Targeted validation: 14 passed.
- Full `python -m market_analyzer.main` completed successfully.
- NIFTY50 benchmark comparison is now valid after date normalization.
- Current nested-OOS research backtest:
  - CAGR: 3.3399%
  - volatility: 15.9583%
  - Sharpe: 0.2861
  - Sortino: 0.2993
  - max drawdown: -39.7169%
  - total turnover: 1311.38
  - total transaction/slippage cost: 0.91796
- NIFTY50 over the same comparison period:
  - total return: 175.63%
  - CAGR: 9.2035%
  - volatility: 16.1219%
  - Sharpe: 0.6274
  - Sortino: 0.9630
  - max drawdown: -38.4399%
- Interpretation: this is the first materially trustworthy performance baseline after removing retrospective final-ensemble/risk-feature contamination. It should replace the earlier 50%+ CAGR / Sharpe ~2.4 figures as the research baseline; those earlier figures were produced by contaminated methodology.
- Current production signal output is predominantly negative/neutral and the optimizer allocated 0% to all six assets, so the live decision path is currently effectively cash. This is a model/output behavior to investigate, not a reason to alter gates merely to force exposure.
- Remaining blockers before expanded retraining remain: point-in-time historical universe enforcement, historical cross-sectional context availability, external fundamentals/news timestamps, fold-specific regime/anomaly/crash semantics, residual unexplained/post-gap price jumps and symbol-history handling.
- Next methodological work should diagnose the weak OOS result with simple baselines, fold/time-period/regime breakdowns, feature/model ablations, and signal/coverage diagnostics before hyperparameter tuning or expanded retraining.


## SESSION STOPPOINT — 2026-09-27

### Current verified state
- Goal 3 dashboard work remains completed and runtime-verified.
- Goal 1 data-quality/leakage work progressed substantially.
- Targeted validation currently passes: **14 passed in 1.66s**.
- Full `PYTHONPATH=src python -m market_analyzer.main` completes successfully.
- Current production date: 2026-09-25.
- Do not treat this as a fresh project. Read this handover and inspect the current code before making further changes.

### Leakage/OOS methodology now in place
- Base forecasters are evaluated walk-forward.
- Historical ensemble evaluation is strictly nested: each ensemble test fold is trained only on earlier OOS base predictions.
- Historical meta-training excludes `crash_probability`, `regime_probability`, and `anomaly_score` because those outputs were previously produced by final/latest risk-model fits rather than fold-specific historical fits.
- Historical research backtest uses nested OOS ensemble predictions rather than the final production ensemble.
- Ensemble-only historical signals now receive neutral defaults for unavailable historical risk outputs instead of importing final/latest risk predictions.
- Backtest dates are normalized internally to pandas datetime.
- Regression coverage exists in `tests/test_backtest_oos.py`.
- Leakage tests cover target boundaries, walk-forward boundaries, fold isolation, availability timestamps, and model target purging.

### Key recent commits
- `26100ae38e8ff1974df11d97bd5b3874298441e3` — nested ensemble/calibration evaluation refactor.
- `ce8f4da000b5d234318b91e389af4b2ca844c370` — normalize ensemble history dates.
- `7e88ea685e140a084d61a16b48ec1093208b1ff4` — use nested OOS predictions for research backtest.
- `d5822132e228c6584884f857e5aebd34b00d9373` — remove non-OOS risk features from historical ensemble.
- `9ea5adb56533243dba71cc87ebf3a7f6db07d760` — OOS backtest regression test.
- `cd0d1015ffe44d08a96ac4076624945e29f027a6` — normalize backtest dates internally.
- `b13c8c1f1e3bda54932b651e268c6d04fad04baf` — correct transaction-cost expectations in regression test.
- `ee6add967ce4806768051c2a28906c53aa3ed823` — use tolerant floating-point assertions.
- `7064250a13e84f7af8b1528d0428c77ac67397f0` — allow ensemble-only OOS signal construction without risk leakage.
- `0a93cf4ad583e715c0775a17f65044e7506b8f65` — remove stale non-OOS risk merge from research backtest.
- `5d419635af8a9283dcbd65f3bbd1de4736734e46` — fix NIFTY50 benchmark date alignment.
- `441fac619ed9f6239d6f7e30b2bb2cf983f76bb0` — record corrected leakage-clean OOS baseline.

### Latest trustworthy OOS baseline
Targeted tests: **14 passed**.

Nested-OOS signal-weighted research backtest:
- CAGR: **3.3399%**
- Volatility: **15.9583%**
- Sharpe: **0.2861**
- Sortino: **0.2993**
- Max drawdown: **-39.7169%**
- Total turnover: **1311.38**
- Total transaction/slippage cost: **0.91796**

NIFTY50 over the same comparison period:
- Total return: **175.63%**
- CAGR: **9.2035%**
- Volatility: **16.1219%**
- Sharpe: **0.6274**
- Sortino: **0.9630**
- Max drawdown: **-38.4399%**
- Hit rate: **53.14%**
- Worst day: **-12.98%**

The earlier reported strategy results around 50%+ CAGR / Sharpe ~2.4 are obsolete as performance evidence because they were generated before the retrospective ensemble/risk-feature leakage was removed. Do not compare them as valid baselines.

### Latest production signal behavior
Latest six-stock production run:
- TCS: NEUTRAL, expected -0.13%, crash 26.9%, anomaly 0.88, confidence 22.1%
- INFY: NEUTRAL, expected -0.18%, crash 12.2%, anomaly 0.76, confidence 1.4%
- RELIANCE: UNDERWEIGHT, expected -0.71%, crash 2.0%, anomaly 0.63, confidence 12.3%
- HDFCBANK: UNDERWEIGHT, expected -0.79%, crash 6.7%, anomaly 0.75, confidence 20.7%
- ICICIBANK: UNDERWEIGHT, expected -0.82%, crash 0.6%, anomaly 0.96, confidence 10.4%
- SBIN: UNDERWEIGHT, expected -0.99%, crash 1.9%, anomaly 0.76, confidence 16.2%

Portfolio target weights were all **0.0%**. INFY was excluded by the confidence gate; the remaining names were technically eligible but had no positive decision score. Do not loosen the gate merely to force exposure.

Stress output was cash-only:
`synthetic_paths=0, horizon=20, cash_only=True`.
This is a consequence of zero target exposure, not evidence that TimeGAN itself has failed.

### Data-quality state
NSE raw store:
- 4,914,061 rows
- 3,796 tickers
- 2015-01-01 → 2026-09-25
- structural raw audit clean for duplicates, missing values, invalid OHLC, nonpositive prices, negative/zero volume.

Corporate-action work:
- 15,651 corporate-action rows acquired/reconciled for the eligible universe.
- Composite bonus/split interpretation fixed for cases such as RAMASTEEL.
- Non-destructive adjusted research frame/store exists.
- Latest adjusted store build:
  - raw_rows=4,914,061
  - parsed_actions=12,530
  - adjustable_actions=445
  - adjusted_rows_written=4,914,061
  - raw_store_unchanged=True
- Continuity classifier:
  - gap_runs=808
  - tickers_with_gaps=327
  - total_missing_sessions=40,747
  - jump_candidates=224
  - exact_action_matches=11
  - adjustable_action_matches=0
  - classification: exact_action 11, near_action_and_post_gap 1, post_gap 126, unexplained 86.
- Do not invent corporate-action adjustments for unexplained jumps. The 86 same-session unexplained jumps remain a direct investigation set; post-gap jumps need separate continuity treatment.

Point-in-time universe audit:
- Full-period eligible universe: 1,133.
- Static full-period universe is survivorship-prone and must not be used as historical training/backtest membership.
- Historical quarterly eligible counts rise from 541 in 2018-04 to 1,104 in 2026-07.
- Registry currently returns zero eligible before 2018-04 under the current 756-session / 70% coverage / liquidity policy. This is a registry-policy limitation, not evidence that NSE had no securities before 2018.
- Historical fold-specific universe membership still needs explicit implementation/policy before expanded retraining.

### Remaining methodological blockers
Before expanded model retraining:
1. Enforce point-in-time universe membership per historical walk-forward fold.
2. Audit historical cross-sectional context; current context is based on the supplied/static symbol universe and may be survivor-biased.
3. Audit external fundamentals/news information availability timestamps. Do not assume publication/fiscal availability from observation dates.
4. Make crash/regime/anomaly outputs genuinely fold-specific if they are to enter historical ensemble/backtest decisions.
5. Investigate the 86 unexplained same-session price jumps and symbol-history/corporate-action discontinuities.
6. Audit calibration separately: current calibrator is fitted on nested OOS predictions, but calibration performance itself is not yet evaluated on a distinct untouched layer.
7. Replace the current signal-weighted backtest with an evaluation of the actual `PortfolioOptimizer` path once data/model semantics are clean.
8. Investigate the weak OOS result using diagnostics before hyperparameter tuning:
   - fold/time-period breakdown
   - signal coverage / exposure
   - positive-signal frequency
   - base-forecaster performance
   - simple baselines
   - feature/model ablations
   - turnover and cost attribution
   - regime/time-period performance
9. Only after these diagnostics should expanded retraining be attempted.

### Important benchmark note
The NIFTY50 benchmark was temporarily all-zero because market dates and Yahoo benchmark dates had different types. This was fixed in `main.py` by normalizing both to pandas datetime before joining. The current 9.2035% CAGR benchmark result is the corrected comparison.

### Exact next resumption point
When work resumes:
1. Pull latest `main`.
2. Read this handover.
3. Manually audit current `main.py`, `decisions/signals.py`, `backtest/engine.py`, `training/leakage.py`, universe/data-quality modules, and current tests.
4. Do **not** immediately retrain.
5. First implement diagnostics for the corrected OOS result, starting with fold-level performance and signal/exposure coverage.
6. Then compare the nested ensemble against its base forecasters and simple baselines.
7. Continue point-in-time universe/context/data-availability work in parallel with the diagnosis.
8. Keep the 3.34% CAGR / 0.286 Sharpe / -39.72% max-DD result as the current research baseline until a methodology change produces a new verified result.

### Working rule
The project is in **validation/data-correctness + model-diagnosis**, not optimization-for-performance mode. Do not tune thresholds, loosen gates, remove safeguards, or alter evaluation methodology merely to improve the displayed backtest numbers.
