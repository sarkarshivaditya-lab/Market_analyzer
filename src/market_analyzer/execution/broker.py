from __future__ import annotations
import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import pandas as pd

@dataclass(frozen=True)
class Order:
    ticker: str
    side: str
    quantity: float
    order_type: str = "market"

class Broker(Protocol):
    def submit(self, order: Order) -> dict: ...

class PaperBroker:
    def __init__(self, starting_cash: float = 100000.0):
        self.cash=float(starting_cash); self.positions={}; self.orders=[]; self.last_prices={}
    def mark_to_market(self, prices: dict[str,float]) -> float:
        self.last_prices.update(prices)
        return self.cash + sum(q*self.last_prices.get(t,0.0) for t,q in self.positions.items())
    def submit(self, order: Order) -> dict:
        if order.side not in {"BUY","SELL"} or order.quantity<=0: raise ValueError("Invalid paper order.")
        current=self.positions.get(order.ticker,0.0)
        if order.side=="SELL" and order.quantity>current: raise ValueError("Paper broker cannot short or oversell a position.")
        if order.side=="BUY":
            self.positions[order.ticker]=current+order.quantity
        else:
            self.positions[order.ticker]=current-order.quantity
        fill={"ticker":order.ticker,"side":order.side,"quantity":float(order.quantity),"status":"FILLED"}
        self.orders.append(fill); return fill

class ZerodhaBroker:
    """Kite Connect order adapter. Requires KITE_API_KEY and KITE_ACCESS_TOKEN."""
    def __init__(self, api_key=None, access_token=None):
        self.api_key=api_key or os.environ["KITE_API_KEY"]; self.access_token=access_token or os.environ["KITE_ACCESS_TOKEN"]
    def submit(self, order: Order) -> dict:
        payload={"exchange":"NSE","tradingsymbol":order.ticker,"transaction_type":order.side,"quantity":int(order.quantity),"order_type":order.order_type.upper(),"product":"CNC","validity":"DAY","variety":"regular"}
        body=urlencode(payload).encode()
        req=Request("https://api.kite.trade/orders/regular",data=body,headers={"Authorization":f"token {self.api_key}:{self.access_token}"},method="POST")
        with urlopen(req,timeout=15) as response: return json.loads(response.read().decode())

class AlpacaBroker:
    """Alpaca REST adapter. Defaults to paper trading unless a live base URL is supplied."""
    def __init__(self, api_key=None, secret_key=None, paper=True):
        self.api_key=api_key or os.environ["ALPACA_API_KEY"]; self.secret_key=secret_key or os.environ["ALPACA_SECRET_KEY"]
        self.base="https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
    def submit(self, order: Order) -> dict:
        payload={"symbol":order.ticker,"qty":str(order.quantity),"side":order.side.lower(),"type":order.order_type.lower(),"time_in_force":"day"}
        req=Request(f"{self.base}/v2/orders",data=json.dumps(payload).encode(),headers={"APCA-API-KEY-ID":self.api_key,"APCA-API-SECRET-KEY":self.secret_key,"Content-Type":"application/json"},method="POST")
        with urlopen(req,timeout=15) as response: return json.loads(response.read().decode())

@dataclass
class ExecutionPolicy:
    paper_only: bool=True
    max_order_notional: float=5000.0
    max_daily_notional: float=20000.0
    require_positive_expected_return: bool=True
    min_confidence: float=.60

class ExecutionEngine:
    def __init__(self,broker: Broker,policy: ExecutionPolicy|None=None):
        self.broker=broker; self.policy=policy or ExecutionPolicy(); self.daily_notional=0.0
        if self.policy.paper_only and not isinstance(broker,PaperBroker):
            raise ValueError("paper_only=True requires PaperBroker.")
    def rebalance(self,targets: pd.DataFrame,prices: dict[str,float],current_positions: dict[str,float]|None=None) -> list[dict]:
        positions=current_positions or {}
        orders=[]
        for row in targets.to_dict("records"):
            ticker=str(row["tic"]); price=float(prices.get(ticker,0.0)); target=float(row.get("target_weight",0.0))
            if price<=0: continue
            target_qty=max(0.0,target*100000.0/price); delta=target_qty-float(positions.get(ticker,0.0))
            if abs(delta*price)<1.0: continue
            side="BUY" if delta>0 else "SELL"
            orders.append({"ticker":ticker,"side":side,"quantity":abs(delta),"order_type":"market"})
        return self.execute(pd.DataFrame(orders),prices) if orders else []
    def execute(self,decisions: pd.DataFrame,prices: dict[str,float]) -> list[dict]:
        results=[]
        for row in decisions.to_dict("records"):
            ticker=str(row["tic"]); expected=float(row.get("ensemble_expected_return",row.get("expected_return",0.0)))
            confidence=float(row.get("ensemble_confidence",row.get("confidence",0.0))); weight=float(row.get("target_weight",0.0))
            price=float(prices.get(ticker,0.0)); notional=min(max(0.0,weight)*100000.0,self.policy.max_order_notional,self.policy.max_daily_notional-self.daily_notional)
            if price<=0 or notional<=0 or (self.policy.require_positive_expected_return and expected<=0) or confidence<self.policy.min_confidence: continue
            result=self.broker.submit(Order(ticker,"BUY",notional/price)); results.append(result); self.daily_notional+=notional
        return results
