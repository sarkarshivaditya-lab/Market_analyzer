"""Yahoo Finance market-data ingestion with NSE symbol normalization."""
from __future__ import annotations

import pandas as pd
import yfinance as yf


def yahoo_symbol(ticker: str) -> str:
    """Map clean NSE symbols to Yahoo's .NS convention."""
    ticker = str(ticker).strip()
    if not ticker:
        raise ValueError("ticker must not be empty")
    if ticker.endswith(".NS") or ticker.startswith("^") or "=" in ticker or ticker.endswith(".BO"):
        return ticker
    return f"{ticker}.NS"


class YahooMarketData:
    def __init__(self, start_date: str, end_date: str, tickers: list[str]):
        if not tickers:
            raise ValueError("tickers must not be empty")
        self.start_date = start_date
        self.end_date = end_date
        self.tickers = tickers

    def fetch(self, auto_adjust: bool = True) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for ticker in self.tickers:
            yahoo_ticker = yahoo_symbol(ticker)
            frame = yf.download(
                yahoo_ticker,
                start=self.start_date,
                end=self.end_date,
                auto_adjust=auto_adjust,
                progress=False,
            )
            if frame.empty:
                continue
            if isinstance(frame.columns, pd.MultiIndex):
                frame.columns = frame.columns.get_level_values(0)
            frame = frame.reset_index()
            rename = {
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adjcp",
                "Volume": "volume",
            }
            frame = frame.rename(columns=rename)
            frame["tic"] = ticker
            required = ["date", "open", "high", "low", "close", "volume", "tic"]
            missing = [col for col in required if col not in frame.columns]
            if missing:
                raise ValueError(f"{ticker}: missing columns {missing}")
            frames.append(frame[required])
        if not frames:
            raise ValueError("No market data was fetched.")
        result = pd.concat(frames, ignore_index=True)
        result["date"] = pd.to_datetime(result["date"]).dt.strftime("%Y-%m-%d")
        result = result.dropna().sort_values(["date", "tic"]).reset_index(drop=True)
        return result


def split_by_date(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    result = df[(df["date"] >= start) & (df["date"] < end)].copy()
    return result.sort_values(["date", "tic"]).reset_index(drop=True)
