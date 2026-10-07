# Market Analyzer — Project Handover

This persistent handover records the validated state of the Market_analyzer project. Re-audit the live repository before material changes.

## Current repository
Repository: sarkarshivaditya-lab/Market_analyzer
Default branch: main.
Current development branch: research/diagnostics-baselines.

The project is an AI-driven Indian-market financial intelligence and portfolio-decision platform. The objective is a functional, sellable system for investors/banks, not an academic-only model.

## Checkpoint 1 — Final comparative evidence (2026-10-07)

The corrected research report has now been generated after fixing the baseline portfolio-accounting bug. Validation is clean:
- Dedicated research diagnostics suite: 9 passed in 0.38s.
- Full regression suite: 126 passed in 6.67s.
- Reproducible report: scripts/generate_research_report.py.
- OOS window: 2018-04-26 through 2026-09-29.

Corrected portfolio-path results:
- ensemble_oos: CAGR 4.2496%, volatility 18.7010%, Sharpe 0.3165, Sortino 0.3927, max drawdown -44.7420%, turnover 1301.0649, cost 0.910745.
- equal_weight: CAGR 10.0961%, volatility 18.8183%, Sharpe 0.6059, Sortino 0.7744, max drawdown -39.9328%, turnover 386.6929, cost 0.270685.
- buy_and_hold: CAGR 13.7453%, volatility 18.8156%, Sharpe 0.7793, Sortino 0.9931, max drawdown -39.6224%, turnover 1.0, cost 0.000700.
- momentum_top3: CAGR -0.5209%, volatility 21.2688%, Sharpe 0.0827, Sortino 0.1012, max drawdown -46.6785%, turnover 1737.3243, cost 1.216127.
- momentum_top3_vol_scaled: CAGR -2.7039%, volatility 20.8953%, Sharpe -0.0258, Sortino -0.0320, max drawdown -47.9985%, turnover 1910.8355, cost 1.337585.
- NIFTY50: CAGR 9.6604%, volatility 16.9946%, Sharpe 0.6284, Sortino 0.7606, max drawdown -38.4399%.
- base_1d: CAGR 10.6770%, volatility 19.3134%, Sharpe 0.6223, Sortino 0.7540, max drawdown -44.1610%, turnover 1380.1861, cost 0.966130.
- base_5d: CAGR 6.4914%, volatility 20.0308%, Sharpe 0.4145, Sortino 0.5125, max drawdown -45.4199%, turnover 1034.3235, cost 0.724026.
- base_20d: CAGR 4.0267%, volatility 20.8392%, Sharpe 0.2944, Sortino 0.3485, max drawdown -44.3285%, turnover 677.3652, cost 0.474156.

Predictive metrics for the base forecasters:
- 1d: 12,510 observations, MAE 0.012548, RMSE 0.018392, directional accuracy 51.3749%.
- 5d: 12,486 observations, MAE 0.030666, RMSE 0.042953, directional accuracy 51.1373%.
- 20d: 12,396 observations, MAE 0.065525, RMSE 0.091289, directional accuracy 53.0090%.

Interpretation:
- The ensemble OOS portfolio proxy does not currently beat NIFTY50, equal-weight, buy-and-hold, or the 1d base forecaster on this OOS window.
- The 1d base forecaster is currently the strongest model-derived portfolio proxy; the ensemble is materially worse despite being built from the base forecasters.
- Buy-and-hold is the strongest simple baseline in this report, while equal-weight also beats NIFTY50 on CAGR/Sharpe over this specific window.
- Momentum baselines are not competitive here, especially after turnover/costs.
- Predictive directional accuracy is only modestly above 50%, so the current evidence does not justify architecture changes based on headline returns alone.
- This is diagnostic evidence, not a production performance claim. The ensemble historical path still uses simplified historical risk inputs, and the actual PortfolioOptimizer has not yet been evaluated OOS.

The previous equal-weight/buy-and-hold equality was a genuine accounting bug: both were effectively fixed-weight paths. The corrected implementation now lets equal-weight rebalance as prices drift while buy-and-hold weights drift without rebalancing. Regression tests explicitly cover this distinction.

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
- a true fixed-weight buy-and-hold path with turnover only on initial establishment

Important baseline interpretation: the generic buy-and-hold helper is a fixed-weight basket path. It must not be described as a NIFTY50 buy-and-hold benchmark unless its input is explicitly a NIFTY50 benchmark/constituent series. NIFTY50 benchmark returns remain separately sourced and date-aligned in the research path.

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

### Validation completed
- Dedicated diagnostics suite: 7 passed in 0.18s.
- Full regression suite: 124 passed in 5.40s.
- Test environment: Python 3.14 with third-party pytest plugin autoload disabled.
- Latest validation commits on this branch include the corrected horizon/signal semantics, true buy-and-hold behavior, and regression tests for both.
- Working-tree policy remains unchanged: local `data/` is intentionally untracked and must not be committed.

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


## Agent tooling — Ponytail (2026-10-07)

Added project-local AGENTS.md based on DietrichGebert/ponytail's AGENTS.md and skills/ponytail/SKILL.md.

The repository now applies Ponytail's full/default engineering mode to coding work: understand and trace first, then prefer YAGNI, existing code, Python stdlib, platform features, existing dependencies, and finally the minimum new code. Root-cause fixes, deletion over addition, fewest files, and runnable checks are preferred.

Ponytail is adapted rather than copied wholesale. Agent/plugin-specific host integrations and unrelated benchmark/assets were intentionally not added to this application repository. Market Analyzer's existing financial-research requirements remain non-negotiable and override simplification whenever needed for leakage prevention, point-in-time correctness, causal timestamps, OOS evaluation, security, data integrity, auditability, reproducibility, or explicit user requirements.

Source repository: https://github.com/DietrichGebert/ponytail (MIT). Source revision reviewed: main branch on 2026-10-07.


## Checkpoint 2 — Fold-level point-in-time universe integration (2026-10-07)

Implemented the first causal universe integration layer:
- `training.walk_forward.split_frame()` now accepts an optional universe reference and evaluates eligible tickers separately at each fold's train and test cutoff.
- `main.py` now passes the feature frame as the fold universe reference, so future rows cannot make a ticker eligible before its fold cutoff.
- Added regression coverage proving a newly appearing ticker is absent from the earlier training fold and can enter only when eligible at the later test cutoff.

This is an important correction but not yet the final survivorship-bias solution. The current feature frame still originates from the selected symbol universe, so securities completely absent from that input universe (for example historical securities that later disappeared) cannot be recovered by fold filtering. The next context/data step must therefore construct the historical security panel from the full NSE store and replace the static survivor-based cross-sectional context with fold/as-of context. Expanded retraining remains blocked until that is complete.

Relevant commits:
- 82e67e2 — fold-level point-in-time universe support
- d983a38 — regression test
- 1d3a92c — integrate PIT universe into main walk-forward path
- 200ffad — correct PIT timing fixture

Validation must be run locally after pulling these commits before treating the checkpoint as complete.

## Exact resumption point
The development branch contains Checkpoint 1 research diagnostics/baseline code and has passed its targeted and full regression suites. Before merging to main:
1. Run the current application path again after the final branch state.
2. Generate the actual six-stock OOS diagnostic report from nested OOS predictions.
3. Compare ensemble/base forecasters and transparent baselines on identical OOS dates.
4. Record the resulting comparative evidence in this handover.
5. Then continue to point-in-time universe/context implementation.

Do not retrain the expanded dataset yet.


## Checkpoint 3 — Full NSE historical panel and point-in-time context (2026-10-08)

Implemented the next survivorship-bias correction layer:
- `NSELocalMarketStore.tickers()` exposes the complete local security universe.
- Registry-mode runs now load the full NSE historical panel for research instead of restricting the feature panel to the final-date 1,133 survivors.
- Walk-forward `split_frame()` now evaluates eligibility against that full historical panel at each train/test cutoff.
- Final production training is restricted back to the eligible universe at the latest training cutoff.
- Final portfolio construction is restricted to the current resolved production symbols, so expanding the research panel does not silently expand the live decision universe.
- `MarketContextData.fetch()` can now consume the local historical panel directly.
- Local context filters securities by their point-in-time history age before calculating breadth/dispersion, preventing future-listed securities from contributing to earlier context.
- Dashboard chart generation remains restricted to the resolved production symbols rather than all historical securities.

This removes the major final-date survivor-panel dependency from the historical walk-forward input. It does not yet constitute the complete universe methodology: context currently enforces point-in-time history availability, while the full liquidity/coverage eligibility rule is still handled by fold-level `split_frame()`. Fundamentals/news timestamp causality and fold-specific crash/regime/anomaly models remain separate blockers.

New regression coverage:
- `tests/test_context.py` verifies a later-listed security does not contribute to earlier local context.

Required validation after pulling:
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src pytest tests/test_context.py tests/test_walk_forward.py tests/test_universe.py tests/test_point_in_time_audit.py -q`
- Then run the broader regression suite before generating a new research report.

Do not retrain the expanded dataset yet.

## Checkpoint 3 validation — clean regression gate (2026-10-08)

The Checkpoint 3 implementation has now been validated locally after the context regression expectation was corrected:
- Targeted PIT/context/universe/audit suite: **13 passed in 0.36s**.
- Full project regression suite: **128 passed in 5.26s**.
- No known regression remains from the full NSE historical research panel, PIT fold filtering, local point-in-time context, or Ponytail engineering rules.

Checkpoint 3 is therefore a clean implementation/testing checkpoint.

The remaining methodological gap is unchanged: local cross-sectional context currently applies point-in-time history availability, but does not yet apply the complete historical liquidity/coverage eligibility rule to each context observation. Expanded retraining remains blocked until this is resolved, along with the separate fundamentals/news causality and fold-specific crash/regime/anomaly requirements.

Next work should tighten the historical context methodology and validate it before any model architecture changes or expanded retraining.
