"""NSE CM Bhavcopy ingestion with local caching and normalized OHLCV output.

The provider supports the current UDiFF daily CM bhavcopy and the legacy
NSE equity bhavcopy for older dates. It is intended for historical/EOD data,
not real-time market data.
"""
from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import requests


BASE_URL = "https://nsearchives.nseindia.com"
UDIFF_START = pd.Timestamp("2024-07-08")
DEFAULT_HEADERS = {
    "User-Agent": "market-analyzer/0.1 educational research",
    "Accept": "text/csv,application/zip,application/octet-stream,*/*",
}


class NSEBhavcopyMarketData:
    """Download NSE cash-market bhavcopy files and normalize them to OHLCV."""

    def __init__(
        self,
        start_date: str,
        end_date: str,
        tickers: list[str] | None = None,
        cache_dir: str | Path = "data/raw/nse",
        session: requests.Session | None = None,
    ):
        self.start_date = pd.Timestamp(start_date).normalize()
        self.end_date = pd.Timestamp(end_date).normalize()
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        self.tickers = {str(x).strip().upper() for x in (tickers or []) if str(x).strip()}
        self.cache_dir = Path(cache_dir)
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    @staticmethod
    def _udiff_url(day: pd.Timestamp) -> str:
        return (
            f"{BASE_URL}/content/cm/"
            f"BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip"
        )

    @staticmethod
    def _legacy_url(day: pd.Timestamp) -> str:
        month = day.strftime("%b").upper()
        return (
            f"{BASE_URL}/content/historical/EQUITIES/"
            f"{day:%Y}/{month}/"
            f"cm{day:%d}{month}{day:%Y}bhav.csv.zip"
        )

    def _url(self, day: pd.Timestamp) -> str:
        return self._udiff_url(day) if day >= UDIFF_START else self._legacy_url(day)

    def _cache_path(self, day: pd.Timestamp) -> Path:
        return self.cache_dir / f"{day:%Y}" / f"cm_{day:%Y%m%d}.zip"

    def _missing_path(self, day: pd.Timestamp) -> Path:
        return self.cache_dir / f"{day:%Y}" / f"cm_{day:%Y%m%d}.missing"

    def _download(self, day: pd.Timestamp) -> bytes | None:
        cache = self._cache_path(day)
        missing = self._missing_path(day)
        if cache.exists():
            return cache.read_bytes()
        if missing.exists():
            return None

        cache.parent.mkdir(parents=True, exist_ok=True)
        response = self.session.get(self._url(day), timeout=45)
        if response.status_code == 404:
            missing.touch()
            return None
        response.raise_for_status()
        if response.content[:2] != b"PK":
            raise ValueError(f"NSE bhavcopy for {day:%Y-%m-%d} is not a valid ZIP archive.")
        cache.write_bytes(response.content)
        return response.content

    @staticmethod
    def _read_zip(blob: bytes) -> pd.DataFrame:
        with ZipFile(BytesIO(blob)) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError("NSE bhavcopy ZIP contains no CSV file.")
            with archive.open(csv_names[0]) as handle:
                return pd.read_csv(handle)

    @staticmethod
    def _normalize_udiff(raw: pd.DataFrame) -> pd.DataFrame:
        required = {
            "TradDt",
            "TckrSymb",
            "SctySrs",
            "OpnPric",
            "HghPric",
            "LwPric",
            "ClsPric",
            "TtlTradgVol",
        }
        missing = required.difference(raw.columns)
        if missing:
            raise ValueError(f"UDiFF bhavcopy missing columns: {sorted(missing)}")
        equity = raw[raw["SctySrs"].astype("string").str.strip().eq("EQ")].copy()
        return pd.DataFrame(
            {
                "date": pd.to_datetime(equity["TradDt"], errors="coerce"),
                "open": pd.to_numeric(equity["OpnPric"], errors="coerce"),
                "high": pd.to_numeric(equity["HghPric"], errors="coerce"),
                "low": pd.to_numeric(equity["LwPric"], errors="coerce"),
                "close": pd.to_numeric(equity["ClsPric"], errors="coerce"),
                "volume": pd.to_numeric(equity["TtlTradgVol"], errors="coerce"),
                "tic": equity["TckrSymb"].astype("string").str.strip().str.upper(),
            }
        )

    @staticmethod
    def _normalize_legacy(raw: pd.DataFrame) -> pd.DataFrame:
        raw = raw.rename(columns=lambda c: str(c).strip().upper())
        required = {"TIMESTAMP", "SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "TOTTRDQTY"}
        missing = required.difference(raw.columns)
        if missing:
            raise ValueError(f"Legacy NSE bhavcopy missing columns: {sorted(missing)}")
        equity = raw[raw["SERIES"].astype("string").str.strip().eq("EQ")].copy()
        return pd.DataFrame(
            {
                "date": pd.to_datetime(equity["TIMESTAMP"], errors="coerce", format="%d-%b-%Y"),
                "open": pd.to_numeric(equity["OPEN"], errors="coerce"),
                "high": pd.to_numeric(equity["HIGH"], errors="coerce"),
                "low": pd.to_numeric(equity["LOW"], errors="coerce"),
                "close": pd.to_numeric(equity["CLOSE"], errors="coerce"),
                "volume": pd.to_numeric(equity["TOTTRDQTY"], errors="coerce"),
                "tic": equity["SYMBOL"].astype("string").str.strip().str.upper(),
            }
        )

    def _normalize(self, raw: pd.DataFrame) -> pd.DataFrame:
        if "TckrSymb" in raw.columns:
            return self._normalize_udiff(raw)
        return self._normalize_legacy(raw)

    def fetch(self) -> pd.DataFrame:
        rows: list[pd.DataFrame] = []
        day = self.start_date
        while day < self.end_date:
            if day.weekday() < 5:
                blob = self._download(day)
                if blob is not None:
                    frame = self._normalize(self._read_zip(blob))
                    if self.tickers:
                        frame = frame[frame["tic"].isin(self.tickers)]
                    rows.append(frame)
            day += timedelta(days=1)

        if not rows:
            raise ValueError("No NSE bhavcopy data was fetched for the requested period.")

        result = pd.concat(rows, ignore_index=True)
        result["date"] = pd.to_datetime(result["date"]).dt.strftime("%Y-%m-%d")
        result = result.dropna(subset=["date", "tic", "open", "high", "low", "close", "volume"])
        result = result.drop_duplicates(["date", "tic"]).sort_values(["date", "tic"]).reset_index(drop=True)
        return result[["date", "open", "high", "low", "close", "volume", "tic"]]
