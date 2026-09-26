from __future__ import annotations
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
app=FastAPI(title="Market Analyzer",version="0.1.0")
_state={"signals":[],"portfolio":[],"brief":"No analysis loaded.","backtest":{}}
def set_state(signals=None,portfolio=None,brief=None,backtest=None):
    if signals is not None:_state["signals"]=signals
    if portfolio is not None:_state["portfolio"]=portfolio
    if brief is not None:_state["brief"]=brief
    if backtest is not None:_state["backtest"]=backtest
@app.get("/health")
def health(): return {"status":"ok"}
@app.get("/api/state")
def state(): return _state
@app.get("/",response_class=HTMLResponse)
def dashboard():
    return """<!doctype html><html><head><meta charset='utf-8'><title>Market Analyzer</title><style>body{font-family:system-ui;margin:40px;max-width:1100px}pre{background:#f4f4f4;padding:16px;overflow:auto}.card{border:1px solid #ddd;border-radius:12px;padding:20px;margin:12px 0}</style></head><body><h1>Market Analyzer</h1><div class='card'><h2>Market brief</h2><pre id='brief'>Loading...</pre></div><div class='card'><h2>Portfolio</h2><pre id='portfolio'>Loading...</pre></div><div class='card'><h2>Backtest</h2><pre id='backtest'>Loading...</pre></div><script>fetch('/api/state').then(r=>r.json()).then(x=>{document.getElementById('brief').textContent=x.brief;document.getElementById('portfolio').textContent=JSON.stringify(x.portfolio,null,2);document.getElementById('backtest').textContent=JSON.stringify(x.backtest,null,2);});</script></body></html>"""
