# Market Analyzer — Project Handover

This persistent handover records the validated state of the Market_analyzer project. Re-audit the live repository before material changes.

## Current repository
Repository: sarkarshivaditya-lab/Market_analyzer
Default branch: main.
Current development branch: research/diagnostics-baselines.

The project is an AI-driven Indian-market financial intelligence and portfolio-decision platform. The objective is a functional, sellable system for investors/banks, not an academic-only model.

## Validation/data methodology status

The historical evaluation path has been made leakage-aware:
- Base forecasting is chronological/walk-forward.
- Historical ensemble predictions are generated in nested fashion using only earlier OOS base predictions.
- Historical ensemble meta-features currently exclude crash/regime/anomaly outputs because those outputs are not yet fold-specific.
- Historical research uses nested OOS ensemble predictions, not the final production ensemble.
- Backtest dates are normalized internally.
- NIFTY50 benchmark date alignment was corrected.
- Mechanical leakage tests cover target boundaries, walk-forward boundaries, fold isolation, availability timestamps, and model target purging.

The expanded retraining remains blocked until point-in-time universe/context and external information availability are resolved.

## Checkpoint 1 — OOS diagnostics and transparent baselines

### Implemented on development branch
Added:
- src/market_analyzer/backtest/diagnostics.py
- src/market_analyzer/backtest/baselines.py
- tests/test_research_diagnostics.py

Diagnostics now provide:
- signal observation/date/ticker coverage
- positive/neutral/negative signal frequency
- exposure and cash-day statistics
- mean/median/total turnover
- transaction-cost attribution
- fold-by-fold strategy versus benchmark returns
- fold Sharpe/hit-rate/turnover/cost metrics
- base forecaster MAE/RMSE/directional accuracy
- a consolidated research-diagnostics result structure

Transparent baseline helpers now provide:
- equal-weight basket
- top-N momentum
- momentum with inverse-volatility scaling
- baseline metric reporting

The backtest research helper benchmark default is now NIFTY50 rather than SPY, matching the Indian product.

### Diagnostic finding from the current six-stock OOS signal path
The current score-to-weight research backtest is not a faithful representation of the PortfolioOptimizer. It clips negative decision scores to zero and normalizes positive scores to 100% gross exposure, producing discontinuous allocation changes.

The latest local diagnostic showed:
- OOS window: 2018-04-26 through 2026-09-29
- CAGR: 7.3875%
- volatility: 18.6546%
- Sharpe: 0.4757
- Sortino: 0.5945
- max drawdown: -45.6404%
- total turnover: 1302.97
- total cost: 0.91208
- mean daily turnover: 0.6099
- median daily turnover: 0.5296
- turnover >= 0.5 on 52.25% of days
- turnover >= 1.0 on 25.98% of days
- turnover >= 1.5 on 4.17% of days
- single-asset days: 7.09%
- cash days: 18.98%
- average holdings: 3.64
- median holdings: 4
- maximum holdings: 6
- score-change mean: 0.00448
- score-change median: 0.00274
- consecutive-day score and weight Pearson correlations were reported as 1.0 for every stock

Interpretation: raw model outputs are comparatively smooth; the high turnover is materially driven by the discontinuous positive-score normalization and should not yet be attributed to unstable forecasting alone.

### Important correction
The earlier 3.3399% CAGR / 0.2861 Sharpe / -39.7169% max-DD figure was a leakage-clean baseline but used a date scope that included observations outside the actual nested-OOS signal availability window. The 7.3875% result above is a diagnostic OOS-window calculation using the nested OOS signals. It is still a signal-weighted research proxy, not the final optimizer evaluation.

Do not use either result as a claim of predictive superiority. The benchmark and baselines must be measured over exactly the same OOS dates.

## Active goals

### Goal 1 — Maximize useful data and retrain
Current progress:
- NSE CM-UDiFF daily store exists locally.
- Raw store covers 2015-01-01 through 2026-09-25 and contains 3,796 tickers / 4,914,061 rows.
- Point-in-time universe registry exists.
- Corporate-action history has been acquired for the current eligible universe.
- Separate adjusted research store exists without mutating raw data.
- Continuity audit identifies residual unexplained jumps and post-gap issues.

Remaining blockers before expanded retraining:
1. Enforce point-in-time universe membership inside every historical walk-forward fold.
2. Eliminate survivor/static-universe bias from historical cross-sectional context.
3. Audit fundamentals/news using explicit information-availability timestamps.
4. Make crash/regime/anomaly historical predictions genuinely fold-specific before using them as meta-features.
5. Resolve residual unexplained same-session jumps and symbol-history issues.
6. Audit calibration on a distinct untouched evaluation layer.

### Goal 2 — Refine the algorithm from evidence
Required order:
1. Complete diagnostics and baselines.
2. Compare nested ensemble to each base forecaster.
3. Perform feature/model ablations.
4. Analyze regime/time-period performance.
5. Evaluate turnover/cost sensitivity.
6. Only then make targeted architecture or hyperparameter changes.
7. After each material change, rerun strict chronological/OOS evaluation.

Do not loosen gates or alter evaluation definitions merely to improve reported numbers.

### Goal 3 — Product/dashboard
Trader-oriented graphical dashboard is already implemented and runtime-verified. Remaining dashboard work is regression hardening, not redesign.

## Current architecture
Data: market/Yahoo/NSE-local, macro, context, fundamentals, news, Zerodha.
Features: technical engineering and cross-sectional context.
Models: multi-horizon forecasting, crash risk, regime, anomaly, stacked ensemble, calibration, TimeGAN stress.
Decision/risk: investment signals, portfolio gate, covariance-aware PortfolioOptimizer.
Research: backtest engine, research helpers, diagnostics, transparent baselines.
Execution: paper broker/session plus guarded broker scaffolding.
Dashboard: FastAPI server-rendered workstation with persisted chart-ready state.

## Safety/research rules
- Never use future information.
- Never put credentials in source control.
- No live execution by default.
- Treat historical news/fundamentals as causal only when availability timestamps are enforced.
- Do not present retrospective in-sample model output as OOS evidence.
- Keep paper trading separate from live execution.
- Every material model change requires regression coverage and OOS comparison.

## Exact resumption point
The development branch contains Checkpoint 1 research diagnostics/baseline code. Before merging to main:
1. Run the targeted research tests.
2. Run the full suite with third-party pytest autoload disabled in the current Python 3.14 environment.
3. Run the current application path.
4. Generate the actual six-stock OOS diagnostic report from nested OOS predictions.
5. Compare ensemble/base forecasters and transparent baselines on identical dates.
6. Commit/update this handover with verified test/runtime numbers.
7. Then continue to point-in-time universe/context implementation.

Do not retrain the expanded dataset yet.
