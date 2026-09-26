from market_analyzer.dashboard.app import dashboard, health, set_state, state

def test_dashboard_health_and_state():
    assert health()["status"]=="ok"
    set_state(signals=[{"tic":"SPY"}],portfolio=[{"tic":"SPY","target_weight":1.0}],brief="ready")
    payload=state()
    assert payload["brief"]=="ready"
    assert payload["signals"][0]["tic"]=="SPY"
    assert payload["portfolio"][0]["target_weight"]==1.0

def test_dashboard_page_loads():
    page=dashboard()
    assert isinstance(page,str)
    assert "Market Analyzer" in page
    assert "/api/state" in page
