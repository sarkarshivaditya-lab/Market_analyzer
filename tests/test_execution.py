from market_analyzer.execution.broker import ExecutionEngine,ExecutionPolicy,PaperBroker,Order
import pandas as pd
import pytest

def test_paper_only_gate():
    class Fake: pass
    with pytest.raises(ValueError):
        ExecutionEngine(Fake(),ExecutionPolicy(paper_only=True))

def test_paper_execution():
    e=ExecutionEngine(PaperBroker(),ExecutionPolicy(min_confidence=.5))
    out=e.execute(pd.DataFrame([{"tic":"AAA","ensemble_expected_return":.1,"ensemble_confidence":.9,"target_weight":.02}]),{"AAA":100})
    assert out and out[0]["status"]=="FILLED"

def test_execute_can_reduce_existing_position():
    broker=PaperBroker(starting_cash=10000)
    broker.submit(Order("AAA","BUY",50,price=100))
    engine=ExecutionEngine(broker,ExecutionPolicy(min_confidence=.5,max_order_notional=10000,max_daily_notional=10000),capital=10000)
    out=engine.execute(pd.DataFrame([{"tic":"AAA","ensemble_expected_return":-.1,"ensemble_confidence":.9,"target_weight":0.0}]),{"AAA":100})
    assert out and out[0]["side"]=="SELL"
    assert out[0]["quantity"]==50
    assert broker.positions["AAA"]==0

def test_execute_filters_new_buys_by_expected_return_and_confidence():
    broker=PaperBroker(starting_cash=10000)
    engine=ExecutionEngine(broker,ExecutionPolicy(min_confidence=.6),capital=10000)
    decisions=pd.DataFrame([
        {"tic":"NEG","ensemble_expected_return":-.1,"ensemble_confidence":.9,"target_weight":.1},
        {"tic":"LOWCONF","ensemble_expected_return":.1,"ensemble_confidence":.2,"target_weight":.1},
        {"tic":"OK","ensemble_expected_return":.1,"ensemble_confidence":.9,"target_weight":.1},
    ])
    out=engine.execute(decisions,{"NEG":100,"LOWCONF":100,"OK":100})
    assert len(out)==1
    assert out[0]["ticker"]=="OK"

def test_live_execution_requires_explicit_environment_gate(monkeypatch):
    class FakeBroker:
        def submit(self, order): return {"status":"ACCEPTED"}
    with pytest.raises(ValueError,match="MARKET_ANALYZER_LIVE_TRADING"):
        ExecutionEngine(FakeBroker(),ExecutionPolicy(paper_only=False))

def test_live_execution_gate_allows_configured_broker(monkeypatch):
    monkeypatch.setenv("MARKET_ANALYZER_LIVE_TRADING","CONFIRMED")
    class FakeBroker:
        def submit(self, order): return {"status":"ACCEPTED"}
    engine=ExecutionEngine(FakeBroker(),ExecutionPolicy(paper_only=False,min_confidence=.5),capital=10000)
    out=engine.execute(pd.DataFrame([{"tic":"AAA","ensemble_expected_return":.1,"ensemble_confidence":.9,"target_weight":.02}]),{"AAA":100})
    assert out[0]["status"]=="ACCEPTED"


def test_broker_paper_flag_is_explicit():
    assert PaperBroker().paper is True
