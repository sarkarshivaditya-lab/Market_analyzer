from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app=FastAPI(title="Market Analyzer",version="0.1.0")
STATE_FILE=Path(os.getenv("MARKET_ANALYZER_STATE_FILE",Path(tempfile.gettempdir())/"market_analyzer_state.json"))
_state={"signals":[],"portfolio":[],"brief":"No analysis loaded.","backtest":{},"stress":{}}

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

def set_state(signals=None,portfolio=None,brief=None,backtest=None,stress=None):
    if signals is not None:_state["signals"]=signals
    if portfolio is not None:_state["portfolio"]=portfolio
    if brief is not None:_state["brief"]=brief
    if backtest is not None:_state["backtest"]=backtest
    if stress is not None:_state["stress"]=stress
    try:
        STATE_FILE.parent.mkdir(parents=True,exist_ok=True)
        with STATE_FILE.open("w",encoding="utf-8") as f:
            json.dump(_state,f,ensure_ascii=False)
    except OSError:
        pass

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/api/state")
def state(): return _load_state()

@app.get("/",response_class=HTMLResponse)
def dashboard():
    return """<!doctype html><html><head><meta charset='utf-8'><title>Market Analyzer</title><style>body{font-family:system-ui;margin:40px;max-width:1100px}pre{background:#f4f4f4;padding:16px;overflow:auto}.card{border:1px solid #ddd;border-radius:12px;padding:20px;margin:12px 0}</style></head><body><h1>Market Analyzer</h1><div class='card'><h2>Market brief</h2><pre id='brief'>Loading...</pre></div><div class='card'><h2>Portfolio</h2><pre id='portfolio'>Loading...</pre></div><div class='card'><h2>Backtest</h2><pre id='backtest'>Loading...</pre></div><div class='card'><h2>TimeGAN stress test</h2><pre id='stress'>Loading...</pre></div><script>fetch('/api/state').then(r=>r.json()).then(x=>{document.getElementById('brief').textContent=x.brief;document.getElementById('portfolio').textContent=JSON.stringify(x.portfolio,null,2);document.getElementById('backtest').textContent=JSON.stringify(x.backtest,null,2);document.getElementById('stress').textContent=JSON.stringify(x.stress,null,2);});</script></body></html>"""
