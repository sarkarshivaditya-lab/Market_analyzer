import io
from zipfile import ZipFile

import pandas as pd

from market_analyzer.data.nse import NSEBhavcopyMarketData


def _zip_csv(text: str) -> bytes:
    buf = io.BytesIO()
    with ZipFile(buf, "w") as archive:
        archive.writestr("BhavCopy.csv", text)
    return buf.getvalue()


def test_nse_udiff_normalization():
    raw = pd.DataFrame(
        [
            {
                "TradDt": "2026-09-25",
                "TckrSymb": "INFY",
                "SctySrs": "EQ",
                "OpnPric": 1500,
                "HghPric": 1520,
                "LwPric": 1490,
                "ClsPric": 1510,
                "TtlTradgVol": 100000,
            },
            {
                "TradDt": "2026-09-25",
                "TckrSymb": "NIFTY",
                "SctySrs": "INDEX",
                "OpnPric": 1,
                "HghPric": 1,
                "LwPric": 1,
                "ClsPric": 1,
                "TtlTradgVol": 1,
            },
        ]
    )
    out = NSEBhavcopyMarketData._normalize_udiff(raw)
    assert out.to_dict("records") == [
        {
            "date": pd.Timestamp("2026-09-25"),
            "open": 1500,
            "high": 1520,
            "low": 1490,
            "close": 1510,
            "volume": 100000,
            "tic": "INFY",
        }
    ]


def test_nse_fetch_caches_and_filters(monkeypatch, tmp_path):
    client = NSEBhavcopyMarketData(
        "2026-09-25",
        "2026-09-26",
        tickers=["INFY"],
        cache_dir=tmp_path,
    )
    payload = _zip_csv(
        "TradDt,TckrSymb,SctySrs,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol\n"
        "2026-09-25,INFY,EQ,1500,1520,1490,1510,100000\n"
        "2026-09-25,TCS,EQ,3000,3050,2990,3030,200000\n"
    )

    calls = []

    class Response:
        status_code = 200
        content = payload

        def raise_for_status(self):
            pass

    def fake_get(url, timeout):
        calls.append(url)
        return Response()

    monkeypatch.setattr(client.session, "get", fake_get)

    first = client.fetch()
    second = client.fetch()

    assert len(first) == 1
    assert first.iloc[0]["tic"] == "INFY"
    assert first.iloc[0]["close"] == 1510
    assert len(calls) == 1
    assert "20260925" in calls[0]


def test_nse_legacy_url_is_used_before_udiff():
    client = NSEBhavcopyMarketData("2024-07-05", "2024-07-06", tickers=["INFY"])
    assert "/content/historical/EQUITIES/2024/JUL/cm05JUL2024bhav.csv.zip" in client._url(pd.Timestamp("2024-07-05"))
    assert "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20240708_F_0000.csv.zip" == client._url(pd.Timestamp("2024-07-08"))
