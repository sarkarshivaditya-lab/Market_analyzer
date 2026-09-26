from __future__ import annotations
import pandas as pd

def build_market_brief(signals: pd.DataFrame, portfolio: pd.DataFrame) -> str:
    latest=signals.sort_values("date").groupby("tic").tail(1)
    lines=["MARKET ANALYZER — MARKET INTELLIGENCE BRIEF",f"Data date: {latest['date'].max()}",""]
    for _,row in latest.sort_values("decision_score",ascending=False).iterrows():
        lines.append(f"{row['tic']}: {row['signal']} | regime={row.get('regime_label','unknown')} | expected {row['expected_return']:.2%} | crash risk {row['crash_probability']:.1%} | anomaly {row['anomaly_score']:.2f} | confidence {row['confidence']:.1%}")
    lines.append("")
    lines.append("TARGET PORTFOLIO")
    for _,row in portfolio.iterrows():
        lines.append(f"{row['tic']}: {row['target_weight']:.1%} | {row['signal']} | {row['risk_state']}")
    lines.append("")
    lines.append("These outputs are model signals for validation and decision support; they are not guarantees of future returns.")
    return "\n".join(lines)
