# Market Analyzer

Research platform for market-regime analysis, anomaly detection, crash-risk research, forecasting, and investment brief generation.

## Architecture

1. Data ingestion: Yahoo Finance OHLCV data.
2. Feature engineering: technical indicators, returns, volatility, VIX, and cross-asset turbulence.
3. Generative research: PyTorch implementation of the TimeGAN architecture for synthetic financial time-series research.
4. Event detection: configurable anomaly and stress scoring.
5. Forecasting: extensible supervised sequence-model interface.
6. Backtesting: chronological train/validation/test separation.
7. Reporting: structured market brief output.

This repository is a research system. It does not automatically place real-money trades.

## Upstream attribution

The project incorporates concepts and/or adapted code patterns from:

- TimeGAN by Jinsung Yoon, Daniel Jarrett, and Mihaela van der Schaar: https://github.com/jsyoon0823/TimeGAN
  License: Apache License 2.0.
  Paper: "Time-series Generative Adversarial Networks", NeurIPS 2019.
- FinRL by AI4Finance Foundation: https://github.com/AI4Finance-Foundation/FinRL
  License: MIT.
  FinRL name and logo are trademarks; this repository does not use the FinRL branding.

The project is not affiliated with or endorsed by either upstream project.

## Initial scope

The first milestone is a reproducible research pipeline, not production trading. Any later brokerage integration should be isolated behind explicit risk controls, paper-trading validation, compliance review, and human authorization.
