import pytest

from market_analyzer.execution.broker import Order, PaperBroker

def test_paper_broker_updates_cash_and_positions():
    broker = PaperBroker(starting_cash=1000)
    broker.submit(Order("SPY", "BUY", 2, price=100))
    assert broker.cash == 800
    assert broker.positions["SPY"] == 2
    broker.submit(Order("SPY", "SELL", 1, price=110))
    assert broker.cash == 910
    assert broker.positions["SPY"] == 1

def test_paper_broker_rejects_unpriced_orders():
    broker = PaperBroker(starting_cash=1000)
    with pytest.raises(ValueError, match="fill price"):
        broker.submit(Order("SPY", "BUY", 1))


def test_execution_engine_uses_configured_capital():
    from market_analyzer.execution.broker import ExecutionEngine, ExecutionPolicy
    import pandas as pd
    broker = PaperBroker(starting_cash=5000)
    engine = ExecutionEngine(broker, ExecutionPolicy(max_order_notional=10000), capital=5000)
    targets = pd.DataFrame([{"tic": "SPY", "target_weight": 0.5}])
    results = engine.rebalance(targets, {"SPY": 100})
    assert results[0]["quantity"] == 25.0


def test_execution_engine_rejects_nonpositive_capital():
    from market_analyzer.execution.broker import ExecutionEngine
    with pytest.raises(ValueError, match="capital"):
        ExecutionEngine(PaperBroker(), capital=0)
