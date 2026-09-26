from __future__ import annotations
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
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
    price: float | None = None

class Broker(Protocol):
    def submit(self, order: Order) -> dict: ...

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class PaperBroker:
    """Deterministic paper account with optional JSON persistence."""
    def __init__(self, starting_cash: float = 100000.0, state_file: str | Path | None = None):
        if starting_cash < 0:
            raise ValueError("Starting paper cash cannot be negative.")
        self.state_file=Path(state_file) if state_file else None
        self.cash=float(starting_cash)
        self.positions: dict[str,float]={}
        self.orders: list[dict]=[]
        self.last_prices: dict[str,float]={}
        self.daily_notional=0.0
        self.daily_date=datetime.now(timezone.utc).date().isoformat()
        if self.state_file and self.state_file.exists():
            self._load()
        elif self.state_file:
            self._save()

    def _roll_daily_notional(self) -> None:
        today=datetime.now(timezone.utc).date().isoformat()
        if today != self.daily_date:
            self.daily_date=today
            self.daily_notional=0.0
            self._save()

    def _save(self) -> None:
        if not self.state_file:
            return
        self.state_file.parent.mkdir(parents=True,exist_ok=True)
        payload={"cash":self.cash,"positions":self.positions,"orders":self.orders,"last_prices":self.last_prices,"daily_notional":self.daily_notional,"daily_date":self.daily_date}
        tmp=self.state_file.with_suffix(self.state_file.suffix+".tmp")
        tmp.write_text(json.dumps(payload,indent=2),encoding="utf-8")
        tmp.replace(self.state_file)

    def _load(self) -> None:
        payload=json.loads(self.state_file.read_text(encoding="utf-8"))
        self.cash=float(payload["cash"])
        self.positions={str(k):float(v) for k,v in payload.get("positions",{}).items()}
        self.orders=list(payload.get("orders",[]))
        self.last_prices={str(k):float(v) for k,v in payload.get("last_prices",{}).items()}
        self.daily_notional=float(payload.get("daily_notional",0.0))
        self.daily_date=str(payload.get("daily_date",datetime.now(timezone.utc).date().isoformat()))
        self._roll_daily_notional()

    def mark_to_market(self, prices: dict[str,float]) -> float:
        self.last_prices.update({str(k):float(v) for k,v in prices.items() if float(v)>0})
        value=self.cash+sum(q*self.last_prices.get(t,0.0) for t,q in self.positions.items())
        self._save()
        return value

    def snapshot(self) -> dict:
        self._roll_daily_notional()
        equity=self.mark_to_market({})
        return {"cash":self.cash,"equity":equity,"positions":dict(self.positions),"daily_notional":self.daily_notional,"orders":len(self.orders)}

    def submit(self, order: Order) -> dict:
        self._roll_daily_notional()
        side=str(order.side).upper()
        if side not in {"BUY","SELL"} or order.quantity<=0:
            raise ValueError("Invalid paper order.")
        current=self.positions.get(order.ticker,0.0)
        if order.price is None or order.price<=0:
            raise ValueError("Paper orders require a positive fill price.")
        notional=float(order.quantity)*float(order.price)
        if side=="SELL" and order.quantity>current:
            raise ValueError("Paper broker cannot short or oversell a position.")
        if side=="BUY":
            if notional>self.cash:
                raise ValueError("Insufficient paper cash for order.")
            self.cash-=notional
            self.positions[order.ticker]=current+order.quantity
        else:
            self.cash+=notional
            remaining=current-order.quantity
            self.positions[order.ticker]=remaining if remaining>1e-12 else 0.0
        self.daily_notional+=notional
        fill={"order_id":f"PAPER-{len(self.orders)+1:06d}","ticker":order.ticker,"side":side,"quantity":float(order.quantity),"price":float(order.price),"notional":notional,"order_type":order.order_type,"status":"FILLED","timestamp":_utc_now()}
        self.orders.append(fill)
        self.last_prices[order.ticker]=float(order.price)
        self._save()
        return fill

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
    def __init__(self,broker: Broker,policy: ExecutionPolicy|None=None,capital: float = 100000.0):
        if capital<=0:
            raise ValueError("Execution capital must be positive.")
        self.broker=broker; self.policy=policy or ExecutionPolicy(); self.capital=float(capital)
        if self.policy.max_order_notional<=0 or self.policy.max_daily_notional<=0:
            raise ValueError("Execution notional limits must be positive.")
        if self.policy.paper_only and not isinstance(broker,PaperBroker):
            raise ValueError("paper_only=True requires PaperBroker.")

    def _daily_notional(self) -> float:
        return float(getattr(self.broker,"daily_notional",0.0))

    def rebalance(self,targets: pd.DataFrame,prices: dict[str,float],current_positions: dict[str,float] | None = None) -> list[dict]:
        positions=current_positions
        if positions is None and isinstance(self.broker,PaperBroker):
            positions=dict(self.broker.positions)
        positions=positions or {}
        results=[]
        for row in targets.to_dict("records"):
            ticker=str(row["tic"]); price=float(prices.get(ticker,0.0))
            if price<=0: continue
            target_qty=max(0.0,float(row.get("target_weight",0.0))*self.capital/price)
            delta=target_qty-float(positions.get(ticker,0.0))
            remaining_daily=self.policy.max_daily_notional-self._daily_notional()
            if remaining_daily<=0: break
            notional=min(abs(delta)*price,self.policy.max_order_notional,remaining_daily)
            if notional<1.0: continue
            qty=notional/price
            side="BUY" if delta>0 else "SELL"
            if side=="SELL" and qty>float(positions.get(ticker,0.0)): qty=float(positions.get(ticker,0.0))
            if qty<=0: continue
            result=self.broker.submit(Order(ticker,side,qty,price=price))
            results.append(result)
            positions[ticker]=float(positions.get(ticker,0.0))+qty if side=="BUY" else float(positions.get(ticker,0.0))-qty
        return results

    def execute(self,decisions: pd.DataFrame,prices: dict[str,float]) -> list[dict]:
        results=[]
        for row in decisions.to_dict("records"):
            ticker=str(row["tic"]); expected=float(row.get("ensemble_expected_return",row.get("expected_return",0.0)))
            confidence=float(row.get("ensemble_confidence",row.get("confidence",0.0))); weight=float(row.get("target_weight",0.0))
            price=float(prices.get(ticker,0.0)); remaining_daily=self.policy.max_daily_notional-self._daily_notional()
            notional=min(max(0.0,weight)*self.capital,self.policy.max_order_notional,remaining_daily)
            if price<=0 or notional<=0 or (self.policy.require_positive_expected_return and expected<=0) or confidence<self.policy.min_confidence: continue
            result=self.broker.submit(Order(ticker,"BUY",notional/price,price=price)); results.append(result)
        return results
