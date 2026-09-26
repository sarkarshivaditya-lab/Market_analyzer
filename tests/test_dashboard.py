import pandas as pd
from fastapi.testclient import TestClient
from market_analyzer.dashboard.app import app, set_state

def test_dashboard_health_and_state():
    client=TestClient(app)
    assert client.get("/health").json()["status"]=="ok"
    set_state(signals=[{"tic":"SPY"}],portfolio=[{"tic":"SPY","target_weight":1.0}],brief="ready")
    payload=client.get("/api/state").json()
    assert payload["brief"]=="ready"
    assert payload["signals"][0]["tic"]=="SPY"
    assert payload["portfolio"][0]["target_weight"]==1.0

def test_dashboard_page_loads():
    client=TestClient(app)
    response=client.get("/")
    assert response.status_code==200
    assert "Market Analyzer" in response.text
