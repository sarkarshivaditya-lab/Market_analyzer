import pandas as pd
from market_analyzer import main


def test_load_market_data_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("MARKET_ANALYZER_MARKET_DATA_PROVIDER","unknown")
    try:
        main.load_market_data(["INFY"],"2026-01-01","2026-01-02")
    except ValueError as exc:
        assert "yahoo" in str(exc)
    else:
        raise AssertionError("unknown provider should fail")


def test_load_market_data_uses_zerodha(monkeypatch):
    seen={}
    class FakeKite:
        def __init__(self):
            pass
        def fetch(self,start,end,symbols):
            seen.update(start=start,end=end,symbols=symbols)
            return pd.DataFrame([{"date":"2026-09-25","tic":"INFY","open":100,"high":101,"low":99,"close":100,"volume":1000}])
    monkeypatch.setenv("MARKET_ANALYZER_MARKET_DATA_PROVIDER","zerodha")
    monkeypatch.setattr(main,"ZerodhaMarketData",FakeKite)
    out=main.load_market_data(["INFY"],"2026-01-01","2026-09-26")
    assert seen=={"start":"2026-01-01","end":"2026-09-26","symbols":["INFY"]}
    assert out.iloc[0]["tic"]=="INFY"
