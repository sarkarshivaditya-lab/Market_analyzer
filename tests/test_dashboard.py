import market_analyzer.dashboard.app as dashboard_app
from market_analyzer.dashboard.app import dashboard, health, set_state, state

def test_dashboard_health_and_state(tmp_path,monkeypatch):
    monkeypatch.setattr(dashboard_app,"STATE_FILE",tmp_path/"dashboard_state.json")
    set_state(signals=[{"tic":"SPY"}],portfolio=[{"tic":"SPY","target_weight":1.0}],brief="ready",backtest={"strategy":{"cagr":0.1}},stress={"p01_return":-0.2})
    assert health()["status"]=="ok"
    payload=state()
    assert payload["brief"]=="ready"
    assert payload["signals"][0]["tic"]=="SPY"
    assert payload["portfolio"][0]["target_weight"]==1.0
    assert payload["backtest"]["strategy"]["cagr"]==0.1
    assert payload["stress"]["p01_return"]==-0.2
    assert payload["updated_at"] is not None

def test_dashboard_page_loads():
    page=dashboard()
    assert isinstance(page,str)
    assert "Market Analyzer" in page
    assert "/api/state" in page or "api/state" in page
    assert "Backtest" in page
    assert "TimeGAN stress test" in page
    assert "Target portfolio" in page
    assert "Market signals" in page
    assert "Expected" in page


def test_dashboard_renders_paper_account(tmp_path,monkeypatch):
    monkeypatch.setattr(dashboard_app,"STATE_FILE",tmp_path/"dashboard_state.json")
    set_state(paper={"snapshot":{"equity":100000,"cash":95000,"daily_notional":5000},"positions":[{"tic":"SPY","quantity":25,"price":200,"actual_weight":0.05}]})
    page=dashboard()
    assert "Paper trading" in page
    assert "Today's notional" in page
    assert "SPY" in page
    assert '"actual_weight": 0.05' in page

def test_dashboard_explains_cash_and_allocation_gate(tmp_path,monkeypatch):
    monkeypatch.setattr(dashboard_app,"STATE_FILE",tmp_path/"dashboard_state.json")
    set_state(portfolio=[
        {"tic":"A","target_weight":0.0,"signal":"NEUTRAL","risk_state":"NORMAL","confidence":0.04,"portfolio_eligible":False,"allocation_reason":"LOW_CONFIDENCE"},
        {"tic":"B","target_weight":0.35,"signal":"OVERWEIGHT","risk_state":"NORMAL","confidence":0.30,"portfolio_eligible":True,"allocation_reason":"ELIGIBLE"},
    ])
    page=dashboard()
    assert "Equity exposure" in page
    assert "Cash" in page
    assert "LOW_CONFIDENCE" in page
    assert "ELIGIBLE" in page


def test_dashboard_state_exposes_graphical_contract(tmp_path,monkeypatch):
    monkeypatch.setattr(dashboard_app,"STATE_FILE",tmp_path/"dashboard_state.json")
    set_state(
        market={"symbols":["RELIANCE"],"default_symbol":"RELIANCE","series":{"RELIANCE":[{"date":"2026-09-25","open":100,"high":105,"low":99,"close":104,"sma20":101,"sma50":98,"bb_upper":108,"bb_lower":94,"signal":"OVERWEIGHT","expected_return":0.03,"confidence":0.7,"crash_probability":0.1}]},"regime":[{"date":"2026-09-25","label":"REGIME_1","probability":0.8}]},
        performance={"series":[{"date":"2026-09-25","strategy_equity":1.0,"benchmark_equity":1.0,"drawdown":0.0,"rolling_sharpe":0.0,"rolling_volatility":0.0,"turnover":0.0,"transaction_cost":0.0}]},
    )
    payload=state()
    assert payload["market"]["default_symbol"]=="RELIANCE"
    assert payload["market"]["series"]["RELIANCE"][0]["close"]==104
    assert payload["performance"]["series"][0]["strategy_equity"]==1.0


def test_dashboard_contains_trader_graphics_contract():
    page=dashboard()
    for marker in ["price-chart","equity-chart","drawdown-chart","rolling-chart","turnover-chart","cost-chart","stress-chart","Target portfolio","Paper trading"]:
        assert marker in page
