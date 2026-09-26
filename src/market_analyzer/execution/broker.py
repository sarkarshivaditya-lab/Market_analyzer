from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

@dataclass(frozen=True)
class Order:
    ticker: str
    side: str
    quantity: float
    order_type: str = "market"

class Broker(Protocol):
    def submit(self, order: Order) -> dict:
        ...

class PaperBroker:
    def __init__(self, starting_cash: float = 100000.0):
        self.cash = float(starting_cash)
        self.positions: dict[str, float] = {}
        self.orders: list[dict] = []
    def submit(self, order: Order) -> dict:
        if order.side not in {"BUY", "SELL"} or order.quantity <= 0:
            raise ValueError("Invalid paper order.")
        current = self.positions.get(order.ticker, 0.0)
        if order.side == "SELL" and order.quantity > current:
            raise ValueError("Paper broker cannot short or oversell a position.")
        self.positions[order.ticker] = current + order.quantity if order.side == "BUY" else current - order.quantity
        fill = {"ticker": order.ticker, "side": order.side, "quantity": float(order.quantity), "status": "FILLED"}
        self.orders.append(fill)
        return fill

@dataclass
class ExecutionPolicy:
    paper_only: bool = True
    max_order_notional: float = 5000.0
    require_positive_expected_return: bool = True
    min_confidence: float = 0.60

class ExecutionEngine:
    def __init__(self, broker: Broker, policy: ExecutionPolicy | None = None):
        self.broker = broker
        self.policy = policy or ExecutionPolicy()
    def execute(self, decisions: pd.DataFrame, prices: dict[str, float]) -> list[dict]:
        results = []
        for row in decisions.to_dict("records"):
            ticker = str(row["tic"])
            expected = float(row.get("ensemble_expected_return", row.get("expected_return", 0.0)))
            confidence = float(row.get("ensemble_confidence", row.get("confidence", 0.0)))
            weight = float(row.get("target_weight", 0.0))
            price = float(prices.get(ticker, 0.0))
            notional = min(max(0.0, weight) * 100000.0, self.policy.max_order_notional)
            if price <= 0 or notional <= 0:
                continue
            if self.policy.require_positive_expected_return and expected <= 0:
                continue
            if confidence < self.policy.min_confidence:
                continue
            results.append(self.broker.submit(Order(ticker, "BUY", notional / price)))
        return results
