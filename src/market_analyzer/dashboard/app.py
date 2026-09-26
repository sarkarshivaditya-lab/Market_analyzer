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
_state={"signals":[],"portfolio":[],"brief":"No analysis loaded.","backtest":{},"stress":{},"paper":{},"market":{},"performance":{},"updated_at":None}

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

def set_state(signals=None,portfolio=None,brief=None,backtest=None,stress=None,paper=None,market=None,performance=None):
    if signals is not None:_state["signals"]=signals
    if portfolio is not None:_state["portfolio"]=portfolio
    if brief is not None:_state["brief"]=brief
    if backtest is not None:_state["backtest"]=backtest
    if stress is not None:_state["stress"]=stress
    if paper is not None:_state["paper"]=paper
    if market is not None:_state["market"]=market
    if performance is not None:_state["performance"]=performance
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

def _empty(text):
    return f"<div class='empty'>{html.escape(text)}</div>"

@app.get("/",response_class=HTMLResponse)
def dashboard():
    return """<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Market Analyzer — NSE Workstation</title>
<style>
:root{--bg:#07111f;--panel:#0d1a2b;--panel2:#101f33;--text:#e7edf6;--muted:#91a0b5;--line:#1d3048;--accent:#4ea1ff;--up:#36d399;--down:#fb7185;--warn:#fbbf24;--purple:#a78bfa}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
.container{max-width:1500px;margin:0 auto;padding:18px 20px 50px}.topbar{display:flex;justify-content:space-between;gap:18px;align-items:center;padding:6px 0 18px}
h1{font-size:24px;margin:0;letter-spacing:-.4px}h2{font-size:14px;text-transform:uppercase;letter-spacing:.08em;margin:0;color:#dce6f4}h3{font-size:13px;margin:0;color:#c9d5e5}
.sub{color:var(--muted);font-size:12px;margin-top:4px}.meta{font-size:11px;color:var(--muted);text-align:right}
.toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.select{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.btn{background:var(--panel2);color:var(--muted);border:1px solid var(--line);border-radius:7px;padding:7px 10px;font-size:11px;cursor:pointer}.btn.active{color:var(--text);border-color:var(--accent)}
.grid{display:grid;gap:10px}.overview{grid-template-columns:repeat(5,minmax(0,1fr))}.main{grid-template-columns:minmax(0,2.3fr) minmax(280px,.7fr)}.two{grid-template-columns:repeat(2,minmax(0,1fr))}.three{grid-template-columns:repeat(3,minmax(0,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:13px;min-width:0}.card-head{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:10px}
.metric{min-height:76px}.label{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.value{font-size:23px;font-weight:700;margin-top:6px}.small-value{font-size:16px}.up{color:var(--up)}.down{color:var(--down)}.warn{color:var(--warn)}.purple{color:var(--purple)}
canvas{display:block;width:100%;height:300px}.chart-lg canvas{height:420px}.chart-sm canvas{height:220px}.chart-xs canvas{height:180px}
.chart-wrap{position:relative}.tooltip{position:absolute;display:none;pointer-events:none;background:#07111f;border:1px solid #31445d;border-radius:6px;padding:7px 9px;font-size:10px;line-height:1.55;color:#dce6f4;z-index:3;white-space:nowrap}
.legend{display:flex;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:10px}.legend span{display:inline-flex;align-items:center;gap:5px}.dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.risk-grid{display:grid;gap:9px}.risk-row{display:grid;grid-template-columns:72px 1fr 54px;gap:8px;align-items:center;font-size:11px}.track{height:7px;background:#17283e;border-radius:99px;overflow:hidden}.fill{height:100%;border-radius:99px}
.signal{display:inline-flex;padding:3px 7px;border-radius:999px;font-size:10px;font-weight:700}.signal.up{background:#073a2a}.signal.down{background:#431925}.signal.neutral{background:#1b293a;color:var(--muted)}
.alloc{display:grid;gap:7px}.alloc-row{display:grid;grid-template-columns:60px 1fr 48px;gap:8px;align-items:center;font-size:11px}.alloc-bar{height:9px;background:#17283e;border-radius:99px;overflow:hidden}.alloc-bar i{display:block;height:100%;background:var(--accent)}
.kpi-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.kpi{padding:9px;border:1px solid var(--line);border-radius:7px;background:#0b1727}.kpi .label{font-size:9px}.kpi .value{font-size:16px}
.regime{display:flex;height:34px;border-radius:6px;overflow:hidden;background:#132238}.regime-segment{height:100%;min-width:2px;position:relative}.regime-segment:hover{filter:brightness(1.2)}.regime-label{font-size:9px;white-space:nowrap;overflow:hidden;padding:10px 5px;color:#06101c;font-weight:700}
.position{display:grid;grid-template-columns:65px 1fr 70px;gap:8px;align-items:center;font-size:11px;padding:7px 0;border-bottom:1px solid var(--line)}.position:last-child{border-bottom:0}
.empty{color:var(--muted);font-size:11px;padding:28px 8px;text-align:center}.status{font-size:10px;color:var(--muted)}
pre{white-space:pre-wrap;font:11px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;color:#b7c5d7;margin:0;max-height:180px;overflow:auto}
.note{font-size:10px;color:var(--muted);margin-top:7px}.section-gap{margin-top:10px}
@media(max-width:1100px){.overview{grid-template-columns:repeat(3,minmax(0,1fr))}.main,.two,.three{grid-template-columns:1fr}}
@media(max-width:650px){.container{padding:12px}.overview{grid-template-columns:repeat(2,minmax(0,1fr))}.value{font-size:19px}.topbar{align-items:flex-start;flex-direction:column}.meta{text-align:left}.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style></head>
<body><main class='container'>
<header class='topbar'><div><h1>Market Analyzer <span class='status'>NSE WORKSTATION</span></h1><div class='sub'>Signals, risk, portfolio construction, research performance and paper execution</div></div>
<div class='meta'>State endpoint: <strong>/api/state</strong><br><span id='updated'>Loading…</span></div></header>

<section class='grid overview' id='overview'></section>

<section class='grid main section-gap'>
<div class='card chart-lg'><div class='card-head'><div><h2>Market signals · Price & model signal</h2><div class='sub' id='chart-sub'>Select an NSE stock</div></div><div class='toolbar'><select id='ticker' class='select'></select><button class='btn range active' data-range='90'>3M</button><button class='btn range' data-range='252'>1Y</button><button class='btn range' data-range='0'>ALL</button></div></div>
<div class='chart-wrap'><canvas id='price-chart'></canvas><div class='tooltip' id='price-tip'></div></div>
<div class='legend'><span><i class='dot' style='background:#4ea1ff'></i>Close</span><span><i class='dot' style='background:#36d399'></i>SMA20</span><span><i class='dot' style='background:#a78bfa'></i>SMA50</span><span><i class='dot' style='background:#91a0b5'></i>Bollinger</span><span>▲ Overweight</span><span>▼ Underweight</span></div></div>
<div class='card'><div class='card-head'><div><h2>Model state</h2><div class='sub' id='signal-date'>Latest observation</div></div></div><div id='risk-panel'></div></div>
</section>

<section class='grid two section-gap'>
<div class='card'><div class='card-head'><div><h2>Market regime</h2><div class='sub'>Cross-sectional mode of model regime labels</div></div><span id='regime-now' class='signal neutral'>UNKNOWN</span></div><div id='regime-bar' class='regime'></div><div class='note'>Regime probability is model output; labels are descriptive clusters, not forecasts.</div></div>
<div class='card'><div class='card-head'><div><h2>Target portfolio</h2><div class='sub'>Optimizer output and allocation gates</div></div><span id='portfolio-state' class='signal neutral'>NO DATA</span></div><div id='allocation' class='alloc'></div></div>
</section>

<section class='grid two section-gap'>
<div class='card chart-lg'><div class='card-head'><div><h2>Backtest · Strategy vs NIFTY 50</h2><div class='sub'>Indexed equity curve from the existing backtest</div></div></div><canvas id='equity-chart'></canvas></div>
<div class='card chart-lg'><div class='card-head'><div><h2>Drawdown</h2><div class='sub'>Strategy peak-to-trough path</div></div></div><canvas id='drawdown-chart'></canvas></div>
</section>

<section class='grid three section-gap'>
<div class='card chart-sm'><div class='card-head'><h2>Rolling risk</h2></div><canvas id='rolling-chart'></canvas></div>
<div class='card chart-sm'><div class='card-head'><h2>Turnover</h2></div><canvas id='turnover-chart'></canvas></div>
<div class='card chart-sm'><div class='card-head'><h2>Transaction costs</h2></div><canvas id='cost-chart'></canvas></div>
</section>

<section class='grid two section-gap'>
<div class='card chart-sm'><div class='card-head'><div><h2>TimeGAN stress test</h2><div class='sub'>Distribution of synthetic portfolio-horizon returns</div></div><span id='stress-status' class='signal neutral'>NO DATA</span></div><canvas id='stress-chart'></canvas><div id='stress-kpis' class='kpi-grid'></div></div>
<div class='card chart-sm'><div class='card-head'><div><h2>Paper trading</h2><div class='sub'>Paper account only — live execution remains disabled</div></div></div><div id='paper-kpis' class='kpi-grid'></div><div class='chart-xs'><canvas id='paper-equity-chart'></canvas></div><div id='paper-positions'></div><div class='note'>Paper equity history is displayed when persisted by the account state; otherwise the panel remains a current-account snapshot.</div></div>
</section>

<section class='card section-gap'><div class='card-head'><div><h2>Model brief</h2><div class='sub'>Generated from the existing analysis pipeline</div></div></div><pre id='brief'>No analysis loaded.</pre></section>
</main>
<script>
const fmtPct=(v,d=1)=>Number.isFinite(Number(v))?(Number(v)*100).toFixed(d)+'%':'—';
const fmtNum=(v,d=2)=>Number.isFinite(Number(v))?Number(v).toFixed(d):'—';
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
const finite=v=>Number.isFinite(Number(v));
let state=null,currentTicker=null,currentRange=90;

function ctx(canvas){const r=canvas.getBoundingClientRect(),d=window.devicePixelRatio||1;canvas.width=Math.max(1,r.width*d);canvas.height=Math.max(1,r.height*d);const c=canvas.getContext('2d');c.setTransform(d,0,0,d,0,0);return {c,w:r.width,h:r.height};}
function bounds(values,pad=.08){const a=values.filter(finite).map(Number);if(!a.length)return [0,1];let lo=Math.min(...a),hi=Math.max(...a);if(lo===hi){lo-=1;hi+=1}const p=(hi-lo)*pad;return [lo-p,hi+p]}
function lineChart(id,series,labels,opts={}){
 const canvas=document.getElementById(id);const {c,w,h}=ctx(canvas);c.clearRect(0,0,w,h);if(!series.length||!series[0].values.some(finite)){c.fillStyle='#91a0b5';c.font='12px system-ui';c.fillText('No chart data available',14,24);return}
 const left=42,right=10,top=10,bottom=24,iw=w-left-right,ih=h-top-bottom;
 const all=series.flatMap(s=>s.values).filter(finite);let [lo,hi]=bounds(all,opts.pad??.08);
 c.strokeStyle='#1d3048';c.lineWidth=1;c.font='9px system-ui';c.fillStyle='#91a0b5';
 for(let i=0;i<4;i++){const y=top+ih*i/3;c.beginPath();c.moveTo(left,y);c.lineTo(w-right,y);c.stroke();c.fillText((hi-(hi-lo)*i/3).toFixed(opts.decimals??2),2,y+3)}
 series.forEach(s=>{c.strokeStyle=s.color;c.lineWidth=s.width||1.5;c.beginPath();let started=false;s.values.forEach((v,i)=>{if(!finite(v)){started=false;return}const x=left+(i/(s.values.length-1||1))*iw,y=top+(hi-Number(v))/(hi-lo)*ih;if(!started){c.moveTo(x,y);started=true}else c.lineTo(x,y)});c.stroke()});
 if(labels?.length){c.fillStyle='#6f8096';c.fillText(labels[0]||'',left,h-7);c.textAlign='right';c.fillText(labels[labels.length-1]||'',w-right,h-7);c.textAlign='left'}
}
function drawPrice(){
 const canvas=document.getElementById('price-chart');const {c,w,h}=ctx(canvas);c.clearRect(0,0,w,h);
 const rows=state?.market?.series?.[currentTicker]||[];const data=currentRange?rows.slice(-currentRange):rows.slice();
 if(!data.length){c.fillStyle='#91a0b5';c.font='12px system-ui';c.fillText('No price history available',14,24);return}
 const left=48,right=12,top=14,bottom=28,iw=w-left-right,ih=h-top-bottom;
 const vals=data.flatMap(r=>[r.high,r.low,r.bb_upper,r.bb_lower]).filter(finite).map(Number);let [lo,hi]=bounds(vals,.06);
 const x=i=>left+(i/(data.length-1||1))*iw, y=v=>top+(hi-Number(v))/(hi-lo)*ih;
 c.strokeStyle='#1d3048';c.font='9px system-ui';c.fillStyle='#91a0b5';
 for(let i=0;i<5;i++){const yy=top+ih*i/4;c.beginPath();c.moveTo(left,yy);c.lineTo(w-right,yy);c.stroke();c.fillText((hi-(hi-lo)*i/4).toFixed(0),5,yy+3)}
 const candleW=Math.max(2,Math.min(12,iw/data.length*.62));
 data.forEach((r,i)=>{if(!finite(r.open)||!finite(r.close))return;const xx=x(i);c.strokeStyle=Number(r.close)>=Number(r.open)?'#36d399':'#fb7185';c.lineWidth=1;c.beginPath();c.moveTo(xx,y(r.low));c.lineTo(xx,y(r.high));c.stroke();c.fillStyle=c.strokeStyle;const yy=y(r.open),yc=y(r.close);c.fillRect(xx-candleW/2,Math.min(yy,yc),candleW,Math.max(1,Math.abs(yc-yy)))});
 const drawLine=(key,color)=>{c.strokeStyle=color;c.lineWidth=1.2;c.beginPath();let s=false;data.forEach((r,i)=>{if(!finite(r[key])){s=false;return}const xx=x(i),yy=y(r[key]);if(!s){c.moveTo(xx,yy);s=true}else c.lineTo(xx,yy)});c.stroke()};
 drawLine('sma20','#36d399');drawLine('sma50','#a78bfa');
 c.strokeStyle='#91a0b5';c.lineWidth=1;c.setLineDash([3,3]);drawLine('bb_upper','#91a0b5');drawLine('bb_lower','#91a0b5');c.setLineDash([]);
 data.forEach((r,i)=>{if(!finite(r.close)||!r.signal)return;const xx=x(i),yy=y(r.low);if(String(r.signal).includes('OVERWEIGHT')){c.fillStyle='#36d399';c.beginPath();c.moveTo(xx,yy+12);c.lineTo(xx-5,yy+21);c.lineTo(xx+5,yy+21);c.closePath();c.fill()}else if(String(r.signal).includes('UNDERWEIGHT')){c.fillStyle='#fb7185';c.beginPath();c.moveTo(xx,y(r.high)-12);c.lineTo(xx-5,y(r.high)-21);c.lineTo(xx+5,y(r.high)-21);c.closePath();c.fill()}});
 c.fillStyle='#6f8096';c.fillText(data[0].date,left,h-8);c.textAlign='right';c.fillText(data[data.length-1].date,w-right,h-8);c.textAlign='left';
 canvas._priceData={data,x,y,left,top,iw,ih};
}
function attachPriceTooltip(){
 const canvas=document.getElementById('price-chart'),tip=document.getElementById('price-tip');canvas.onmousemove=e=>{const p=canvas._priceData;if(!p)return;const r=canvas.getBoundingClientRect(),mx=e.clientX-r.left;let i=Math.round((mx-p.left)/p.iw*(p.data.length-1));i=Math.max(0,Math.min(p.data.length-1,i));const d=p.data[i];tip.style.display='block';tip.style.left=Math.min(r.width-175,Math.max(5,mx+10))+'px';tip.style.top='12px';tip.innerHTML='<b>'+esc(d.date)+'</b><br>O '+fmtNum(d.open)+' · H '+fmtNum(d.high)+' · L '+fmtNum(d.low)+' · C '+fmtNum(d.close)+'<br>Expected '+fmtPct(d.expected_return,2)+' · Confidence '+fmtPct(d.confidence)+' · Crash '+fmtPct(d.crash_probability);};canvas.onmouseleave=()=>tip.style.display='none';
}
function renderOverview(){
 const signals=state.signals||[],latest=signals[0]||{},p=state.portfolio||[],w=p.reduce((a,r)=>a+Math.max(0,Number(r.target_weight)||0),0),cash=Math.max(0,1-w),s=state.stress||{};
 document.getElementById('overview').innerHTML=[
 ['Market regime',latest.regime_label||'UNKNOWN',''],
 ['Risk state',latest.risk_state||'NORMAL',latest.risk_state==='HIGH_CRASH_RISK'?'warn':''],
 ['Equity exposure',fmtPct(w),''],
 ['Cash',fmtPct(cash),''],
 ['Stress P05',fmtPct(s.p05_return,2),s.p05_return<0?'down':'up']
 ].map(x=>'<div class="card metric"><div class="label">'+x[0]+'</div><div class="value '+x[2]+'">'+esc(x[1])+'</div></div>').join('');
}
function renderTicker(){
 const symbols=state.market?.symbols||Object.keys(state.market?.series||{});const sel=document.getElementById('ticker');sel.innerHTML=symbols.map(s=>'<option value="'+esc(s)+'">'+esc(s)+'</option>').join('');
 currentTicker=state.market?.default_symbol||symbols[0]||null;if(symbols.includes(currentTicker))sel.value=currentTicker;sel.onchange=()=>{currentTicker=sel.value;updateStock()};attachPriceTooltip();
}
function updateStock(){
 drawPrice();attachPriceTooltip();const rows=state.market?.series?.[currentTicker]||[],latest=rows[rows.length-1]||{};
 document.getElementById('chart-sub').textContent=currentTicker?(currentTicker+' · '+(latest.date||'No date')):'No stock selected';
 document.getElementById('signal-date').textContent=latest.date||'Latest observation';
 const conf=Number(latest.confidence),crash=Number(latest.crash_probability),exp=Number(latest.expected_return),anom=Number(latest.anomaly_score||0);
 document.getElementById('risk-panel').innerHTML='<div class="kpi-grid"><div class="kpi"><div class="label">Signal</div><div class="value small-value">'+esc(latest.signal||'—')+'</div></div><div class="kpi"><div class="label">Expected return</div><div class="value small-value '+(exp>=0?'up':'down')+'">'+fmtPct(exp,2)+'</div></div><div class="kpi"><div class="label">Confidence</div><div class="value small-value">'+fmtPct(conf)+'</div></div></div><div class="risk-grid" style="margin-top:12px"><div class="risk-row"><span>Crash risk</span><div class="track"><div class="fill" style="width:'+Math.max(0,Math.min(100,crash*100))+'%;background:#fb7185"></div></div><b>'+fmtPct(crash)+'</b></div><div class="risk-row"><span>Anomaly</span><div class="track"><div class="fill" style="width:'+Math.max(0,Math.min(100,anom*100))+'%;background:#fbbf24"></div></div><b>'+fmtNum(anom)+'</b></div></div><div class="note">Signal markers are drawn on the price series at the dates where the model emitted an OVERWEIGHT or UNDERWEIGHT decision.</div>';
}
function renderRegime(){
 const r=state.market?.regime||[];const bar=document.getElementById('regime-bar');if(!r.length){bar.innerHTML='<div class="empty">No regime history</div>';return}
 const groups=[];r.forEach(x=>{const last=groups[groups.length-1];if(last&&last.label===x.label)last.count++;else groups.push({label:x.label,count:1,start:x.date,end:x.date})});groups.forEach((g,i)=>{g.end=r.find((x,j)=>j===r.length-1||r[j+1].date===x.date&&false)?.date||g.end});
 const colors=['#4ea1ff','#36d399','#a78bfa','#fbbf24','#fb7185'];bar.innerHTML=groups.map((g,i)=>'<div class="regime-segment" title="'+esc(g.label)+'" style="width:'+Math.max(2,g.count/r.length*100)+'%;background:'+colors[i%colors.length]+'"><div class="regime-label">'+esc(g.label)+'</div></div>').join('');
 const last=r[r.length-1];document.getElementById('regime-now').textContent=last.label||'UNKNOWN';document.getElementById('regime-now').className='signal '+(String(last.label||'').toLowerCase().includes('risk')?'down':'neutral');
}
function renderAllocation(){
 const rows=(state.portfolio||[]).slice().sort((a,b)=>(Number(b.target_weight)||0)-(Number(a.target_weight)||0));const total=rows.reduce((a,r)=>a+Math.max(0,Number(r.target_weight)||0),0);
 document.getElementById('portfolio-state').textContent=total<=0?'CASH ONLY':(total<.5?'LOW CONVICTION':'INVESTED');
 document.getElementById('allocation').innerHTML=rows.length?rows.map(r=>{const w=Math.max(0,Number(r.target_weight)||0);return '<div class="alloc-row"><b>'+esc(r.tic)+'</b><div class="alloc-bar"><i style="width:'+Math.min(100,w*100)+'%"></i></div><span>'+fmtPct(w)+'</span></div>'}).join(''):'<div class="empty">No portfolio allocation loaded</div>';
}
function renderPerformance(){
 const rows=state.performance?.series||[];const dates=rows.map(x=>x.date);
 lineChart('equity-chart',[{values:rows.map(x=>x.strategy_equity),color:'#4ea1ff',width:2},{values:rows.map(x=>x.benchmark_equity),color:'#91a0b5',width:1.5}],dates,{decimals:2});
 lineChart('drawdown-chart',[{values:rows.map(x=>x.drawdown),color:'#fb7185',width:2}],dates,{decimals:2});
 lineChart('rolling-chart',[{values:rows.map(x=>x.rolling_sharpe),color:'#36d399',width:1.8},{values:rows.map(x=>x.rolling_volatility),color:'#a78bfa',width:1.5}],dates,{decimals:2});
 lineChart('turnover-chart',[{values:rows.map(x=>x.turnover),color:'#4ea1ff',width:1.5}],dates,{decimals:0,pad:.18});
 lineChart('cost-chart',[{values:rows.map(x=>x.transaction_cost),color:'#fbbf24',width:1.5}],dates,{decimals:4,pad:.18});
}
function renderStress(){
 const s=state.stress||{},d=Array.isArray(s.distribution)?s.distribution.filter(finite).map(Number):[];const canvas=document.getElementById('stress-chart');const {c,w,h}=ctx(canvas);c.clearRect(0,0,w,h);
 document.getElementById('stress-status').textContent=s.cash_only?'CASH ONLY':(s.collapsed?'COLLAPSED':'ACTIVE');document.getElementById('stress-status').className='signal '+(s.collapsed?'down':'neutral');
 document.getElementById('stress-kpis').innerHTML=[['Mean',fmtPct(s.mean_return,2)],['P05',fmtPct(s.p05_return,2)],['P01',fmtPct(s.p01_return,2)],['Worst DD',fmtPct(s.worst_mean_drawdown,2)]].map(x=>'<div class="kpi"><div class="label">'+x[0]+'</div><div class="value small-value">'+x[1]+'</div></div>').join('');
 if(!d.length){c.fillStyle='#91a0b5';c.font='12px system-ui';c.fillText(s.cash_only?'TimeGAN not applicable while portfolio is 100% cash':'No stress distribution available',14,24);return}
 const left=35,right=10,top=10,bottom=24,iw=w-left-right,ih=h-top-bottom,[lo,hi]=bounds(d,.04),bins=24,counts=new Array(bins).fill(0);
 d.forEach(v=>counts[Math.max(0,Math.min(bins-1,Math.floor((v-lo)/(hi-lo||1)*bins)))]++);
 const max=Math.max(...counts,1);c.fillStyle='#4ea1ff';counts.forEach((n,i)=>{const bw=iw/bins-2,x=left+i*iw/bins+1,y=top+ih-n/max*ih;c.fillRect(x,y,bw,n/max*ih)});c.strokeStyle='#1d3048';c.beginPath();c.moveTo(left,top+ih);c.lineTo(w-right,top+ih);c.stroke();c.fillStyle='#91a0b5';c.font='9px system-ui';c.fillText(fmtPct(lo,1),left,h-7);c.textAlign='right';c.fillText(fmtPct(hi,1),w-right,h-7);c.textAlign='left';
}
function renderPaper(){
 const p=state.paper||{},snap=p.snapshot||{},positions=p.positions||[];document.getElementById('paper-kpis').innerHTML=[['Equity',fmtNum(snap.equity)],['Cash',fmtNum(snap.cash)],["Today's notional",fmtNum(snap.daily_notional)]].map(x=>'<div class="kpi"><div class="label">'+x[0]+'</div><div class="value small-value">'+x[1]+'</div></div>').join('');
 const history=Array.isArray(p.equity_history)?p.equity_history:[];const paperSeries=history.length?history.map(x=>Number(x.equity)):([Number(snap.equity)||0]);const paperDates=history.length?history.map(x=>String(x.timestamp||'').slice(0,10)):['current'];lineChart('paper-equity-chart',[{values:paperSeries,color:'#36d399',width:1.8}],paperDates,{decimals:0,pad:.04});\n document.getElementById('paper-positions').innerHTML=positions.length?positions.map(r=>'<div class="position"><b>'+esc(r.tic)+'</b><span>'+fmtNum(r.quantity,2)+' @ '+fmtNum(r.price)+'</span><b>'+fmtPct(r.actual_weight)+'</b></div>').join(''):'<div class="empty">No open paper positions</div>';
}
function renderBrief(){document.getElementById('brief').textContent=state.brief||'No analysis loaded.';document.getElementById('updated').textContent=state.updated_at?'Updated '+state.updated_at:'No analysis state loaded'}
function render(){renderOverview();renderTicker();updateStock();renderRegime();renderAllocation();renderPerformance();renderStress();renderPaper();renderBrief()}
document.querySelectorAll('.range').forEach(b=>b.onclick=()=>{document.querySelectorAll('.range').forEach(x=>x.classList.remove('active'));b.classList.add('active');currentRange=Number(b.dataset.range);drawPrice()});
window.addEventListener('resize',()=>{if(state){drawPrice();renderPerformance();renderStress()}});
fetch('/api/state').then(r=>r.json()).then(x=>{state=x;render()}).catch(()=>{state={signals:[],portfolio:[],market:{},performance:{},stress:{},paper:{},brief:'Unable to load dashboard state.'};render()});
</script></body></html>"""

