import os

from market_analyzer.main import _resolve_symbols


def test_resolve_symbols_keeps_default_small_universe(monkeypatch):
    monkeypatch.delenv("MARKET_ANALYZER_UNIVERSE", raising=False)
    assert _resolve_symbols(None, "2015-01-01", "2026-09-27") == [
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN"
    ]


def test_registry_mode_requires_local_nse_provider(monkeypatch):
    monkeypatch.setenv("MARKET_ANALYZER_UNIVERSE", "registry")
    monkeypatch.setenv("MARKET_ANALYZER_MARKET_DATA_PROVIDER", "yahoo")
    try:
        _resolve_symbols(None, "2015-01-01", "2026-09-27")
    except ValueError as exc:
        assert "requires MARKET_ANALYZER_MARKET_DATA_PROVIDER=nse_local" in str(exc)
    else:
        raise AssertionError("expected provider guard")
