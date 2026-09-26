import market_analyzer.dashboard.app as dashboard_app
from market_analyzer.dashboard.app import dashboard, health, set_state, state

def test_dashboard_health_and_state(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_app,"STATE_FILE",tmp_path/"dashboard_state.json")
    set_state(signals=[{"tic":"SPY"}],portfolio=[{"tic":"SPY","target_weight":1.0}],brief="ready",backtest={"strategy":{"cagr":0.1}})
    assert health()["status"]=="ok"
    payload=state()
    assert payload["brief"]=="ready"
    assert payload["signals"][0]["tic"]=="SPY"
    assert payload["portfolio"][0]["target_weight"]==1.0
    assert payload["backtest"]["strategy"]["cagr"]==0.1

def test_dashboard_page_loads():
    page=dashboard()
    assert isinstance(page,str)
    assert "Market Analyzer" in page
    assert "/api/state" in page
    assert "Backtest" in page
