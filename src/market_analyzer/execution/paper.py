from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from market_analyzer.execution.broker import ExecutionEngine,ExecutionPolicy,PaperBroker

@dataclass
class PaperTradingSession:
    """Small operational wrapper for repeated paper rebalances."""
    broker: PaperBroker
    engine: ExecutionEngine

    @classmethod
    def create(cls,capital: float=100000.0,state_file: str | None=None,policy: ExecutionPolicy | None=None):
        broker=PaperBroker(starting_cash=capital,state_file=state_file)
        engine=ExecutionEngine(broker,policy=policy,capital=capital)
        return cls(broker,engine)

    def rebalance(self,targets: pd.DataFrame,prices: dict[str,float]) -> dict:
        orders=self.engine.rebalance(targets,prices)
        equity=self.broker.mark_to_market(prices)
        snapshot=self.broker.snapshot()
        position_rows=[]
        for ticker,quantity in snapshot["positions"].items():
            price=float(self.broker.last_prices.get(ticker,0.0))
            position_rows.append({"tic":ticker,"quantity":quantity,"price":price,"market_value":quantity*price})
        for row in position_rows:
            row["actual_weight"]=row["market_value"]/equity if equity else 0.0
        return {"orders":orders,"snapshot":snapshot,"equity":equity,"positions":position_rows}
