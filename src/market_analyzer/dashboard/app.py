from __future__ import annotations
import html
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app=FastAPI(title="Market Analyzer",version="0.1.0")
STATE_FILE=Path(os.getenv("MARKET_ANALYZER_STATE_FILE",Path(tempfile.gettempdir())/"market_analyzer_state.json"))
_state={"signals":[],"portfolio":[],"brief":"No analysis loaded.","backtest":{},"stress":{},"paper":{},"updated_at":None}

def _load_state():
    global _state
    try:
        if STATE_FILE.exists():
            with STATE_FILE.open("r",encoding="utf-8") as f:
                loaded=json.load(f)
            if isinstance(loaded,dict):
                _state.update(loaded)
    except (OSError,json.JSONDecodeError):
        pass
    return _state

def set_state(signals=None,portfolio=None,brief=None,backtest=None,stress=None,paper=None):
    if signals is not None:_state["signals"]=signals
    if portfolio is not None:_state["portfolio"]=portfolio
    if brief is not None:_state["brief"]=brief
    if backtest is not None:_state["backtest"]=backtest
    if stress is not None:_state["stress"]=stress
    if paper is not None:_state["paper"]=paper
    _state["updated_at"]=datetime.now(timezone.utc).isoformat()
    try:
        STATE_FILE.parent.mkdir(parents=True,exist_ok=True)
        with STATE_FILE.open("w",encoding="utf-8") as f:
            json.dump(_state,f,ensure_ascii=False)
    except OSError:
        pass

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/api/state")
def state():
    return _load_state()

def _pct(value,digits=1):
    try:return f"{float(value):.{digits}%}"
    except (TypeError,ValueError):return "—"

def _num(value,digits=2):
    try:return f"{float(value):.{digits}f}"
    except (TypeError,ValueError):return "—"

def _signal_class(value):
    value=str(value or "").upper()
    if "OVERWEIGHT" in value:return "positive"
    if "UNDERWEIGHT" in value:return "negative"
    return "neutral"

def _risk_class(value):
    value=str(value or "").upper()
    if "HIGH" in value or "ANOMALOUS" in value:return "danger"
    if "ELEVATED" in value:return "warning"
    return "safe"

def _render_signals(signals):
    if not signals:return "<div class='empty'>No signal data loaded. Run the analyzer first.</div>"
    rows=[]
    for row in signals:
        tic=html.escape(str(row.get("tic","—")))
        signal=html.escape(str(row.get("signal","—")))
        regime=html.escape(str(row.get("regime_label","—")))
        rows.append(
            f"<tr><td class='ticker'>{tic}</td><td><span class='pill {_signal_class(signal)}'>{signal}</span></td>"
            f"<td>{regime}</td><td>{_pct(row.get('expected_return'))}</td><td>{_pct(row.get('crash_probability'))}</td>"
            f"<td>{_num(row.get('anomaly_score'))}</td><td>{_pct(row.get('confidence'))}</td></tr>"
        )
    return "<table><thead><tr><th>Asset</th><th>Signal</th><th>Regime</th><th>Expected</th><th>Crash risk</th><th>Anomaly</th><th>Confidence</th></tr></thead><tbody>"+"".join(rows)+"</tbody></table>"

def _render_paper(paper):
    if not paper:return "<div class='empty'>No paper-trading account loaded.</div>"
    snapshot=paper.get("snapshot",{})
    positions=paper.get("positions",[])
    rows="".join(f"<tr><td class='ticker'>{html.escape(str(r.get('tic','—')))}</td><td>{_num(r.get('quantity'),4)}</td><td>{_num(r.get('price'),2)}</td><td>{_pct(r.get('actual_weight'))}</td></tr>" for r in positions)
    table="<div class='table-wrap'><table><thead><tr><th>Asset</th><th>Quantity</th><th>Price</th><th>Actual allocation</th></tr></thead><tbody>"+rows+"</tbody></table></div>" if rows else "<div class='empty'>No open paper positions.</div>"
    return "".join([_metric("Equity",_num(snapshot.get("equity"),2)),_metric("Cash",_num(snapshot.get("cash"),2)),_metric("Today's notional",_num(snapshot.get("daily_notional"),2)),table])

def _render_portfolio(portfolio):
    if not portfolio:return "<div class='empty'>No portfolio allocation loaded.</div>"
    total_weight=sum(max(0.0,min(1.0,float(row.get("target_weight",0.0) or 0.0))) for row in portfolio)
    cash_weight=max(0.0,1.0-total_weight)
    eligible_count=sum(bool(row.get("portfolio_eligible",False)) for row in portfolio)
    low_confidence_count=sum(str(row.get("allocation_reason","")).startswith("LOW_CONFIDENCE") for row in portfolio)
    high_crash_count=sum("HIGH_CRASH_RISK" in str(row.get("allocation_reason","")) for row in portfolio)
    status="CASH ONLY" if total_weight <= 1e-9 else ("LOW CONVICTION" if total_weight < 0.5 else "INVESTED")
    status_class="warning" if total_weight <= 1e-9 or total_weight < 0.5 else "safe"
    summary=f"<div class='metrics'><div class='metric'><div class='metric-label'>Equity exposure</div><div class='metric-value'>{total_weight:.1%}</div><div class='metric-sub'>target portfolio</div></div><div class='metric'><div class='metric-label'>Cash</div><div class='metric-value'>{cash_weight:.1%}</div><div class='metric-sub'>unallocated</div></div><div class='metric'><div class='metric-label'>Portfolio state</div><div class='metric-value'><span class='pill {status_class}'>{status}</span></div><div class='metric-sub'>{eligible_count} eligible · {low_confidence_count} low confidence · {high_crash_count} high crash</div></div></div>"
    rows=[]
    for row in portfolio:
        tic=html.escape(str(row.get("tic","—")))
        weight=max(0.0,min(1.0,float(row.get("target_weight",0.0) or 0.0)))
        signal=html.escape(str(row.get("signal","—")))
        risk=html.escape(str(row.get("risk_state","—")))
        reason=html.escape(str(row.get("allocation_reason","—")).replace("_"," "))
        confidence=_pct(row.get("confidence"))
        rows.append(
            f"<div class='allocation'><div class='allocation-head'><span class='ticker'>{tic}</span><span>{weight:.1%}</span></div>"
            f"<div class='bar'><span style='width:{weight*100:.2f}%'></span></div>"
            f"<div class='allocation-meta'><span>{signal} · {confidence} confidence</span><span class='pill {_risk_class(risk)}'>{reason}</span></div></div>"
        )
    return summary+"".join(rows)

def _metric(label,value,sub=""):
    return f"<div class='metric'><div class='metric-label'>{html.escape(label,quote=False)}</div><div class='metric-value'>{html.escape(str(value))}</div><div class='metric-sub'>{html.escape(sub)}</div></div>"

def _render_backtest(backtest):
    strategy=backtest.get("strategy",{}) if isinstance(backtest,dict) else {}
    benchmark=backtest.get("benchmark",{}) if isinstance(backtest,dict) else {}
    return "".join([
        _metric("Strategy CAGR",_pct(strategy.get("cagr")),"annualized"),
        _metric("Strategy Sharpe",_num(strategy.get("sharpe")),"risk-adjusted"),
        _metric("Strategy drawdown",_pct(strategy.get("max_drawdown")),"maximum"),
        _metric("Benchmark CAGR",_pct(benchmark.get("cagr")),"reference"),
        _metric("Benchmark Sharpe",_num(benchmark.get("sharpe")),"risk-adjusted"),
        _metric("Benchmark drawdown",_pct(benchmark.get("max_drawdown")),"maximum"),
    ])

def _render_stress(stress):
    if not stress:return "<div class='empty'>No stress-test result loaded.</div>"
    if stress.get("cash_only"):
        return "<div class='empty'>Portfolio is currently 100% cash; TimeGAN stress testing is not applicable until equity exposure is allocated.</div>"
    collapsed=bool(stress.get("collapsed",False))
    status="COLLAPSED" if collapsed else "DISPERSED"
    status_class="danger" if collapsed else "safe"
    return "".join([
        _metric("Mean return",_pct(stress.get("mean_return"),2),"synthetic horizon"),
        _metric("P05 return",_pct(stress.get("p05_return"),2),"lower-tail"),
        _metric("P01 return",_pct(stress.get("p01_return"),2),"extreme lower-tail"),
        _metric("Worst mean drawdown",_pct(stress.get("worst_mean_drawdown"),2),"path-level"),
        _metric("Path dispersion",_pct(stress.get("path_dispersion"),2),"cross-path"),
        f"<div class='metric'><div class='metric-label'>Generator status</div><div class='metric-value'><span class='pill {status_class}'>{status}</span></div><div class='metric-sub'>{int(stress.get('synthetic_paths',0))} paths · {int(stress.get('horizon',0))}-day horizon</div></div>"
    ])

@app.get("/",response_class=HTMLResponse)
def dashboard():
    data=_load_state()
    signals=data.get("signals",[])
    portfolio=data.get("portfolio",[])
    backtest=data.get("backtest",{})
    stress=data.get("stress",{})
    paper=data.get("paper",{})
    brief=html.escape(str(data.get("brief","No analysis loaded.")))
    updated=html.escape(str(data.get("updated_at") or "Run timestamp not recorded"))
    data_date="Not available"
    if signals:
        data_date=html.escape(str(signals[0].get("date","Not available"))[:10])
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Market Analyzer</title>
<style>
:root{{--bg:#f5f7fb;--card:#fff;--text:#111827;--muted:#6b7280;--line:#e5e7eb;--accent:#2563eb;--positive:#047857;--negative:#b91c1c;--warning:#b45309;--danger:#b91c1c;--safe:#047857}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}}
.container{{max-width:1180px;margin:0 auto;padding:28px 20px 56px}} header{{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:24px}}
h1{{margin:0;font-size:30px;letter-spacing:-.7px}} h2{{margin:0 0 16px;font-size:18px}} p{{color:var(--muted);margin:6px 0 0}}
.header-meta{{text-align:right;color:var(--muted);font-size:13px;line-height:1.6}} button{{border:1px solid var(--line);background:var(--card);border-radius:9px;padding:8px 12px;cursor:pointer;font-weight:600}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;margin:14px 0;box-shadow:0 1px 2px rgba(0,0,0,.03)}}
.grid{{display:grid;grid-template-columns:1fr 2fr;gap:12px}} .metrics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}}
.metric{{border:1px solid var(--line);border-radius:12px;padding:14px;background:#fafafa;min-width:0}} .metric-label{{font-size:12px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.05em}}
.metric-value{{font-size:22px;font-weight:700;margin-top:5px}} .metric-sub{{font-size:12px;color:var(--muted);margin-top:4px}}
table{{width:100%;border-collapse:collapse;font-size:14px}} th,td{{padding:12px 10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}} th{{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}} .ticker{{font-weight:700;letter-spacing:.02em}}
.pill{{display:inline-flex;padding:4px 8px;border-radius:999px;font-size:11px;font-weight:700;white-space:nowrap}} .positive,.safe{{background:#ecfdf5;color:var(--positive)}} .negative,.danger{{background:#fef2f2;color:var(--negative)}} .neutral{{background:#f3f4f6;color:#4b5563}} .warning{{background:#fffbeb;color:var(--warning)}}
.allocation{{padding:11px 0;border-bottom:1px solid var(--line)}} .allocation:last-child{{border-bottom:0}} .allocation-head,.allocation-meta{{display:flex;justify-content:space-between;gap:10px}} .allocation-head{{font-size:14px}} .allocation-meta{{font-size:12px;color:var(--muted);margin-top:7px}}
.bar{{height:8px;background:#edf0f4;border-radius:99px;margin-top:8px;overflow:hidden}} .bar span{{display:block;height:100%;background:var(--accent);border-radius:99px}}
pre{{white-space:pre-wrap;margin:0;color:#374151;font:13px/1.65 ui-monospace,SFMono-Regular,Menlo,monospace}} .empty{{color:var(--muted);padding:8px 0}}
.notice{{font-size:12px;color:var(--muted);margin-top:12px}} .section-head{{display:flex;justify-content:space-between;align-items:center;gap:12px}} .table-wrap{{overflow-x:auto}}
@media(max-width:900px){{.grid{{grid-template-columns:1fr}}.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}header{{align-items:flex-start;flex-direction:column}}.header-meta{{text-align:left}}}}
@media(max-width:560px){{.container{{padding:20px 12px 40px}}.card{{padding:16px;border-radius:14px}}.metrics{{grid-template-columns:1fr}}h1{{font-size:27px}}}}
</style></head>
<body><main class='container'>
<div id='api-state' data-endpoint='/api/state'></div>
<header><div><h1>Market Analyzer</h1><p>Market intelligence, portfolio allocation and stress monitoring</p></div>
<div class='header-meta'>Data date: <strong>{data_date}</strong><br>Updated: {updated}<br><button onclick='location.reload()'>Refresh</button></div></header>

<section class='card'><div class='section-head'><h2>Market signals</h2><span class='pill neutral'>MODEL OUTPUT</span></div>
<div class='table-wrap'>{_render_signals(signals)}</div></section>

<section class='grid'><div class='card'><h2>Target portfolio</h2>{_render_portfolio(portfolio)}</div>
<div class='card'><h2>Backtest</h2><div class='metrics'>{_render_backtest(backtest)}</div></div></section>

<section class='card'><h2>Paper trading</h2>{_render_paper(paper)}</section>

<section class='card'><h2>TimeGAN stress test</h2><div class='metrics'>{_render_stress(stress)}</div></section>

<section class='card'><h2>Model brief</h2><pre>{brief}</pre></section>
</main></body></html>"""
