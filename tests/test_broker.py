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
