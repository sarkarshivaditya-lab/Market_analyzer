import pandas as pd
import pytest
from market_analyzer.execution.broker import ExecutionEngine, ExecutionPolicy, PaperBroker, Order
def test_paper_broker_rejects_oversell():
    with pytest.raises(ValueError): PaperBroker().submit(Order("AAA","SELL",1))
def test_execution_policy_blocks_low_confidence():
    e=ExecutionEngine(PaperBroker(),ExecutionPolicy(min_confidence=.9))
    out=e.execute(pd.DataFrame([{"tic":"AAA","ensemble_expected_return":.1,"ensemble_confidence":.5,"target_weight":.02}]),{"AAA":100})
    assert out==[]
