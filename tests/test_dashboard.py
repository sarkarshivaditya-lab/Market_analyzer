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
    assert "5.0%" in page
