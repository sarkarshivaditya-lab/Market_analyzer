# Market Analyzer

AI-driven financial intelligence and portfolio decision platform.

## Product pipeline

Market data + macro context + point-in-time fundamentals/news
→ feature engine
→ multi-horizon forecasting
→ anomaly detection + regime detection + crash risk
→ leakage-safe ensemble/meta-model
→ probability calibration
→ portfolio optimization
→ benchmarked backtesting
→ TimeGAN stress scenarios
→ market intelligence brief
→ dashboard/API
→ paper trading
→ controlled broker execution.

## Implemented layers

- Yahoo Finance market and macro ingestion with point-in-time backward alignment.
- Cross-sectional breadth, sector leadership, dispersion, and relative-strength context.
- Technical, volatility, drawdown, turbulence, macro, fundamentals, and news features.
- Multi-horizon 1D/5D/20D return forecasting.
- Crash-risk classification and latent market-regime detection.
- Deterministic robust z-score and turbulence anomaly detection.
- Leakage-aware stacked intelligence ensemble.
- Isotonic probability calibration with Brier score, PR-AUC, and log-loss metrics.
- Long-only covariance-aware portfolio optimization with concentration and turnover controls.
- Transaction-cost/slippage-aware backtesting plus benchmark and walk-forward reports.
- PyTorch TimeGAN adaptation for synthetic temporal stress scenarios.
- SEC XBRL fundamentals provider using filing availability as the information boundary.
- Timestamped RSS news ingestion. Historical backtests require a historical news archive; live RSS is not used as historical evidence.
- FastAPI dashboard and JSON state endpoint.
- Paper broker, rebalancing engine, and guarded Zerodha/Alpaca adapters.
- Explicit paper-only default, order-notional limits, daily-notional limits, confidence gates, and positive-expected-return gates.

## Validation principles

1. Features must use information available at prediction time.
2. Forecast targets are purged at their future endpoint.
3. Walk-forward evaluation is chronological.
4. Meta-model training uses out-of-sample base-model predictions.
5. Probability calibration is separated from meta-model training.
6. Backtests include transaction costs and slippage.
7. Synthetic TimeGAN paths are stress scenarios, not evidence of predictive skill.
8. Real-money execution is disabled by default and requires explicit configuration.
9. Broker credentials are supplied through the runtime environment rather than committed to the repository.

## Running

Install dependencies and run the test suite:

    pip install -r requirements.txt
    pip install -e .
    pytest -q

Start the dashboard with:

    uvicorn market_analyzer.dashboard.app:app --host 0.0.0.0 --port 8000

The default execution policy is paper-only. Live broker adapters are isolated behind the ExecutionPolicy(paper_only=False) gate and should only be enabled after independent operational, regulatory, and risk review.

## Important data-provenance note

The SEC provider is suitable for timestamped filing-aware fundamentals. The RSS provider is intended for live context. To train or backtest news-driven models without look-ahead bias, supply a historical news provider whose records include publication timestamps and historical availability.

## Upstream attribution

The repository contains a modern PyTorch adaptation of the TimeGAN architecture and incorporates design patterns inspired by FinRL preprocessing/risk/backtesting workflows. The implementation is maintained as an independent product codebase and does not claim novelty over those established techniques.