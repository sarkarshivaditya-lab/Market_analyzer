import pytest
import pandas as pd
from market_analyzer.execution.broker import Order,PaperBroker,ExecutionEngine,ExecutionPolicy

def test_paper_broker_updates_cash_and_positions():
    broker=PaperBroker(starting_cash=1000)
    broker.submit(Order("SPY","BUY",2,price=100))
    assert broker.cash==800
    assert broker.positions["SPY"]==2
    broker.submit(Order("SPY","SELL",1,price=110))
    assert broker.cash==910
    assert broker.positions["SPY"]==1
    assert broker.orders[-1]["price"]==110
    assert broker.orders[-1]["status"]=="FILLED"

def test_paper_broker_rejects_unpriced_orders():
    broker=PaperBroker(starting_cash=1000)
    with pytest.raises(ValueError,match="fill price"):
        broker.submit(Order("SPY","BUY",1))

def test_paper_broker_persists_account(tmp_path):
    path=tmp_path/"paper.json"
    broker=PaperBroker(starting_cash=1000,state_file=path)
    broker.submit(Order("SPY","BUY",2,price=100))
    restored=PaperBroker(starting_cash=999,state_file=path)
    assert restored.cash==800
    assert restored.positions["SPY"]==2
    assert restored.orders[0]["order_id"]=="PAPER-000001"

def test_execution_engine_uses_configured_capital():
    broker=PaperBroker(starting_cash=5000)
    engine=ExecutionEngine(broker,ExecutionPolicy(max_order_notional=10000),capital=5000)
    targets=pd.DataFrame([{"tic":"SPY","target_weight":0.5}])
    results=engine.rebalance(targets,{"SPY":100})
    assert results[0]["quantity"]==25.0

def test_execution_engine_uses_persisted_positions_for_rebalance(tmp_path):
    broker=PaperBroker(starting_cash=10000,state_file=tmp_path/"paper.json")
    broker.submit(Order("SPY","BUY",25,price=100))
    engine=ExecutionEngine(broker,ExecutionPolicy(max_order_notional=10000,max_daily_notional=10000),capital=10000)
    targets=pd.DataFrame([{"tic":"SPY","target_weight":0.25}])
    results=engine.rebalance(targets,{"SPY":100})
    assert results==[]

def test_execution_engine_daily_limit():
    broker=PaperBroker(starting_cash=10000)
    policy=ExecutionPolicy(max_order_notional=10000,max_daily_notional=1000)
    engine=ExecutionEngine(broker,policy,capital=10000)
    targets=pd.DataFrame([{"tic":"SPY","target_weight":0.5}])
    results=engine.rebalance(targets,{"SPY":100})
    assert results[0]["notional"]==1000
    assert broker.daily_notional==1000

def test_execution_engine_rejects_nonpositive_capital():
    with pytest.raises(ValueError,match="capital"):
        ExecutionEngine(PaperBroker(),capital=0)
