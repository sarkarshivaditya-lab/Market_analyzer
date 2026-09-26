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

def test_portfolio_gate_blocks_low_confidence_and_high_crash():
    from market_analyzer.decisions.signals import apply_portfolio_gate
    frame = pd.DataFrame({
        "tic": ["LOW", "RISK", "OK"],
        "confidence": [0.04, 0.30, 0.30],
        "crash_probability": [0.10, 0.70, 0.10],
    })
    out = apply_portfolio_gate(frame)
    assert out["portfolio_eligible"].tolist() == [False, False, True]
    assert out.loc[out["tic"]=="LOW","allocation_reason"].iloc[0] == "LOW_CONFIDENCE"
    assert out.loc[out["tic"]=="RISK","allocation_reason"].iloc[0] == "HIGH_CRASH_RISK"
    assert out.loc[out["tic"]=="OK","allocation_reason"].iloc[0] == "ELIGIBLE"
