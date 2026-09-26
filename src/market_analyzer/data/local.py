"""Durable local SQLite store for normalized NSE cash-market history."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

_REQUIRED = ["date", "open", "high", "low", "close", "volume", "tic"]


class NSELocalMarketStore:
    """Persist normalized NSE OHLCV locally and query it by date/ticker.

    SQLite is used deliberately: it ships with Python, is transactional, and
    avoids adding a binary dataframe-storage dependency to the research stack.
    """

    def __init__(self, path: str | Path = "data/market/nse.sqlite"):
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS daily_ohlcv (
                date TEXT NOT NULL,
                tic TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                PRIMARY KEY (date, tic)
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_tic_date ON daily_ohlcv(tic,date)")
        return conn

    def upsert(self, frame: pd.DataFrame) -> int:
        missing = set(_REQUIRED).difference(frame.columns)
        if missing:
            raise ValueError(f"Missing market columns: {sorted(missing)}")
        data = frame[_REQUIRED].copy()
        data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        data["tic"] = data["tic"].astype("string").str.strip().str.upper()
        for col in ["open", "high", "low", "close", "volume"]:
            data[col] = pd.to_numeric(data[col], errors="coerce")
        data = data.dropna(subset=_REQUIRED).drop_duplicates(["date", "tic"])
        rows = [tuple(x) for x in data[_REQUIRED].itertuples(index=False, name=None)]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """INSERT INTO daily_ohlcv(date,tic,open,high,low,close,volume)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(date,tic) DO UPDATE SET
                   open=excluded.open,high=excluded.high,low=excluded.low,
                   close=excluded.close,volume=excluded.volume""",
                rows,
            )
        return len(rows)

    def load(self, start: str, end: str, tickers: list[str] | None = None) -> pd.DataFrame:
        params: list[object] = [start, end]
        query = "SELECT date,open,high,low,close,volume,tic FROM daily_ohlcv WHERE date >= ? AND date < ?"
        if tickers:
            clean = sorted({str(x).strip().upper() for x in tickers if str(x).strip()})
            if not clean:
                return pd.DataFrame(columns=_REQUIRED)
            query += " AND tic IN (" + ",".join("?" for _ in clean) + ")"
            params.extend(clean)
        query += " ORDER BY date,tic"
        with self._connect() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def coverage(self, tickers: list[str] | None = None) -> pd.DataFrame:
        query = "SELECT tic,MIN(date) AS first_date,MAX(date) AS last_date,COUNT(*) AS rows FROM daily_ohlcv"
        params: list[object] = []
        if tickers:
            clean = sorted({str(x).strip().upper() for x in tickers if str(x).strip()})
            if clean:
                query += " WHERE tic IN (" + ",".join("?" for _ in clean) + ")"
                params.extend(clean)
        query += " GROUP BY tic ORDER BY tic"
        with self._connect() as conn:
            return pd.read_sql_query(query, conn, params=params)


class NSELocalMarketData:
    """Populate the local store from NSE bhavcopy and serve normalized history."""

    def __init__(self, start_date: str, end_date: str, tickers: list[str] | None = None,
                 store_path: str | Path = "data/market/nse.sqlite",
                 cache_dir: str | Path = "data/raw/nse"):
        from market_analyzer.data.nse import NSEBhavcopyMarketData
        self.provider = NSEBhavcopyMarketData(start_date, end_date, tickers=tickers, cache_dir=cache_dir)
        self.store = NSELocalMarketStore(store_path)
        self.start_date = start_date
        self.end_date = end_date
        self.tickers = tickers

    def fetch(self) -> pd.DataFrame:
        fetched = self.provider.fetch()
        self.store.upsert(fetched)
        return self.store.load(self.start_date, self.end_date, self.tickers)
