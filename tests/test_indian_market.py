from market_analyzer.data.yahoo import yahoo_symbol


def test_nse_symbol_maps_to_yahoo_ns():
    assert yahoo_symbol("RELIANCE") == "RELIANCE.NS"


def test_existing_exchange_and_index_symbols_are_preserved():
    assert yahoo_symbol("TCS.NS") == "TCS.NS"
    assert yahoo_symbol("^NSEI") == "^NSEI"


def test_bse_symbol_is_preserved():
    assert yahoo_symbol("RELIANCE.BO") == "RELIANCE.BO"


def test_indian_context_does_not_require_us_etfs():
    from market_analyzer.data.context import MarketContextData
    context=MarketContextData(breadth_universe=["RELIANCE","TCS"],sector_symbols=["RELIANCE","TCS"])
    assert context.breadth_universe == ["RELIANCE","TCS"]
    assert context.sector_symbols == ["RELIANCE","TCS"]
