import pandas as pd

from market_analyzer.decisions.signals import build_investment_signals

def test_signal_builder_accepts_premerged_risk_columns_without_suffixes():
    frame = pd.DataFrame({
        "date": ["2025-01-01"],
        "tic": ["SPY"],
        "ensemble_expected_return": [0.03],
        "positive_return_probability": [0.70],
        "ensemble_confidence": [0.40],
        "crash_probability": [0.10],
        "regime_probability": [0.80],
        "anomaly_score": [0.20],
        "regime_label": ["bull"],
    })
    empty = pd.DataFrame(columns=["date", "tic"])
    out = build_investment_signals(frame, empty, empty, empty)
    assert "crash_probability" in out.columns
    assert "decision_score" in out.columns
    assert out.loc[0, "decision_score"] > 0
