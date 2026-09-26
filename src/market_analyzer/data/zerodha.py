"""Zerodha Kite Connect market-data client for NSE equities."""
from __future__ import annotations

import os
from io import StringIO
import pandas as pd
import requests


class ZerodhaMarketData:
    """Read-only Kite Connect client for instrument, quote and historical data."""

    base_url = "https://api.kite.trade"

    def __init__(self, api_key: str | None = None, access_token: str | None = None, timeout: float = 15.0):
        self.api_key = api_key or os.environ["KITE_API_KEY"]
        self.access_token = access_token or os.environ["KITE_ACCESS_TOKEN"]
        self.timeout = float(timeout)

    def _headers(self) -> dict[str, str]:
        return {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
        }

    def _get(self, path: str, params: dict | None = None) -> dict:
        response = requests.get(
            f"{self.base_url}{path}",
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(payload.get("message", "Kite API request failed"))
        return payload.get("data")

    def instruments(self, exchange: str = "NSE") -> pd.DataFrame:
        """Download the daily instrument master and return the requested exchange."""
        response = requests.get(
            f"{self.base_url}/instruments/{exchange}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        frame = pd.read_csv(StringIO(response.text))
        if frame.empty:
            raise ValueError(f"Kite returned no instruments for {exchange}")
        return frame

    def resolve_tokens(self, tickers: list[str]) -> dict[str, int]:
        """Resolve NSE tradingsymbols to current instrument tokens."""
        wanted = {str(t).strip().upper() for t in tickers if str(t).strip()}
        if not wanted:
            raise ValueError("tickers must not be empty")
        frame = self.instruments("NSE")
        matches = frame[
            frame["tradingsymbol"].astype(str).str.upper().isin(wanted)
            & frame["segment"].astype(str).eq("NSE")
        ]
        return {
            str(row.tradingsymbol).upper(): int(row.instrument_token)
            for row in matches.itertuples()
        }

    def ltp(self, tickers: list[str]) -> dict[str, float]:
        """Return latest traded prices keyed by NSE:SYMBOL."""
        tokens = [f"NSE:{str(t).strip().upper()}" for t in tickers if str(t).strip()]
        if not tokens:
            raise ValueError("tickers must not be empty")
        data = self._get("/quote/ltp", {"i": tokens})
        return {str(key): float(value["last_price"]) for key, value in data.items()}

    def ohlc(self, tickers: list[str]) -> dict[str, dict]:
        """Return latest OHLC snapshots keyed by NSE:SYMBOL."""
        tokens = [f"NSE:{str(t).strip().upper()}" for t in tickers if str(t).strip()]
        if not tokens:
            raise ValueError("tickers must not be empty")
        return self._get("/quote/ohlc", {"i": tokens})

    def quote(self, tickers: list[str]) -> dict[str, dict]:
        """Return full quote snapshots, including market depth."""
        tokens = [f"NSE:{str(t).strip().upper()}" for t in tickers if str(t).strip()]
        if not tokens:
            raise ValueError("tickers must not be empty")
        return self._get("/quote", {"i": tokens})

    def historical(self, instrument_token: int, start_date: str, end_date: str, interval: str = "day") -> pd.DataFrame:
        """Fetch historical candles for a current instrument token."""
        params = {"from": start_date, "to": end_date}
        data = self._get(f"/instruments/historical/{int(instrument_token)}/{interval}", params)
        candles=data.get("candles",[]) if isinstance(data,dict) else data
        width=7 if candles and len(candles[0])>=7 else 6
        columns=["date","open","high","low","close","volume","oi"][:width]
        frame=pd.DataFrame(candles,columns=columns)
        if "oi" not in frame.columns:
            frame["oi"]=0.0
        if not frame.empty:
            frame["date"] = pd.to_datetime(frame["date"])
        return frame

    def fetch(self, start_date: str, end_date: str, tickers: list[str], interval: str = "day") -> pd.DataFrame:
        """Fetch NSE OHLCV data in the same schema used by the analyzer."""
        if not tickers:
            raise ValueError("tickers must not be empty")
        token_map=self.resolve_tokens(tickers)
        frames=[]
        for ticker in [str(t).strip().upper() for t in tickers]:
            token=token_map.get(ticker)
            if token is None:
                continue
            frame=self.historical(token,start_date,end_date,interval)
            if frame.empty:
                continue
            frame["date"]=pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
            frame["tic"]=ticker
            frames.append(frame[["date","open","high","low","close","volume","tic"]])
        if not frames:
            raise ValueError("No Zerodha market data was fetched.")
        return pd.concat(frames,ignore_index=True).sort_values(["date","tic"]).reset_index(drop=True)

    def historical_for_ticker(self, ticker: str, start_date: str, end_date: str, interval: str = "day") -> pd.DataFrame:
        """Resolve an NSE symbol and fetch its historical candles."""
        symbol = str(ticker).strip().upper()
        tokens = self.resolve_tokens([symbol])
        if symbol not in tokens:
            raise ValueError(f"Kite instrument not found for NSE:{symbol}")
        frame = self.historical(tokens[symbol], start_date, end_date, interval)
        if not frame.empty:
            frame["tic"] = symbol
        return frame
