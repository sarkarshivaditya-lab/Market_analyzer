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
