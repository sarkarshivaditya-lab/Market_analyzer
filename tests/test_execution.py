from market_analyzer.execution.broker import ExecutionEngine,ExecutionPolicy,PaperBroker,ZerodhaBroker,Order
import pandas as pd
import pytest

def test_paper_only_gate():
    class Fake: pass
    with pytest.raises(ValueError): ExecutionEngine(Fake(),ExecutionPolicy(paper_only=True))
def test_paper_execution():
    e=ExecutionEngine(PaperBroker(),ExecutionPolicy(min_confidence=.5))
    out=e.execute(pd.DataFrame([{"tic":"AAA","ensemble_expected_return":.1,"ensemble_confidence":.9,"target_weight":.02}]),{"AAA":100})
    assert out and out[0]["status"]=="FILLED"


def test_live_execution_requires_explicit_environment_gate(monkeypatch):
    class FakeBroker:
        def submit(self, order): return {"status": "ACCEPTED"}
    with pytest.raises(ValueError,match="MARKET_ANALYZER_LIVE_TRADING"):
        ExecutionEngine(FakeBroker(),ExecutionPolicy(paper_only=False))

def test_live_execution_gate_allows_configured_broker(monkeypatch):
    monkeypatch.setenv("MARKET_ANALYZER_LIVE_TRADING","CONFIRMED")
    class FakeBroker:
        def submit(self, order): return {"status": "ACCEPTED"}
    engine=ExecutionEngine(FakeBroker(),ExecutionPolicy(paper_only=False,min_confidence=.5),capital=10000)
    out=engine.execute(pd.DataFrame([{"tic":"AAA","ensemble_expected_return":.1,"ensemble_confidence":.9,"target_weight":.02}]),{"AAA":100})
    assert out[0]["status"]=="ACCEPTED"
