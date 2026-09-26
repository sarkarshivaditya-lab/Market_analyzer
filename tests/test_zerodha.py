import pandas as pd
from market_analyzer.data.zerodha import ZerodhaMarketData


def test_zerodha_ltp_builds_authenticated_request(monkeypatch):
    client=ZerodhaMarketData(api_key="key",access_token="token")
    seen={}

    class Response:
        def raise_for_status(self): pass
        def json(self): return {"status":"success","data":{"NSE:INFY":{"instrument_token":408065,"last_price":1525.5}}}

    def fake_get(url,params=None,headers=None,timeout=None):
        seen.update(url=url,params=params,headers=headers,timeout=timeout)
        return Response()

    monkeypatch.setattr("market_analyzer.data.zerodha.requests.get",fake_get)
    out=client.ltp(["INFY"])
    assert out["NSE:INFY"]==1525.5
    assert seen["params"]["i"]==["NSE:INFY"]
    assert seen["headers"]["Authorization"]=="token key:token"


def test_zerodha_resolves_nse_tokens(monkeypatch):
    client=ZerodhaMarketData(api_key="key",access_token="token")

    def fake_instruments(exchange):
        return pd.DataFrame([
            {"tradingsymbol":"INFY","instrument_token":408065,"segment":"NSE"},
            {"tradingsymbol":"TCS","instrument_token":2953217,"segment":"NSE"},
            {"tradingsymbol":"INFY","instrument_token":999,"segment":"BSE"},
        ])

    monkeypatch.setattr(client,"instruments",fake_instruments)
    assert client.resolve_tokens(["infy","tcs"])=={"INFY":408065,"TCS":2953217}


def test_zerodha_historical_normalizes_candles(monkeypatch):
    client=ZerodhaMarketData(api_key="key",access_token="token")

    monkeypatch.setattr(
        client,
        "_get",
        lambda path,params: [
            ["2026-09-24T09:15:00+0530",100,105,99,103,10000,0],
            ["2026-09-25T09:15:00+0530",103,107,102,106,12000,0],
        ],
    )
    frame=client.historical(408065,"2026-09-24","2026-09-26")
    assert list(frame.columns)==["date","open","high","low","close","volume","oi"]
    assert len(frame)==2
    assert float(frame.iloc[-1]["close"])==106.0


def test_zerodha_historical_for_ticker_adds_ticker(monkeypatch):
    client=ZerodhaMarketData(api_key="key",access_token="token")
    monkeypatch.setattr(client,"resolve_tokens",lambda tickers: {"INFY":408065})
    monkeypatch.setattr(
        client,
        "historical",
        lambda token,start,end,interval: pd.DataFrame([{"date":pd.Timestamp("2026-09-25"),"close":106.0}]),
    )
    frame=client.historical_for_ticker("infy","2026-09-25","2026-09-26")
    assert frame.iloc[0]["tic"]=="INFY"
