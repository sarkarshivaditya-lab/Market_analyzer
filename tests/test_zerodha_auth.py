import hashlib
from market_analyzer.execution.zerodha_auth import exchange_request_token, login_url


def test_login_url_contains_required_parameters():
    url=login_url("abc123")
    assert url=="https://kite.zerodha.com/connect/login?v=3&api_key=abc123"


def test_exchange_request_token_uses_kite_checksum(monkeypatch):
    seen={}
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"status":"success","data":{"access_token":"access","user_id":"AB1234"}}

    def fake_post(url,headers=None,data=None,timeout=None):
        seen.update(url=url,headers=headers,data=data,timeout=timeout)
        return Response()

    monkeypatch.setattr("market_analyzer.execution.zerodha_auth.requests.post",fake_post)
    out=exchange_request_token("request",api_key="key",api_secret="secret")
    expected=hashlib.sha256(b"keyrequestsecret").hexdigest()
    assert out["access_token"]=="access"
    assert seen["url"]=="https://api.kite.trade/session/token"
    assert seen["headers"]["X-Kite-Version"]=="3"
    assert seen["data"]["checksum"]==expected
    assert seen["data"]["api_key"]=="key"
    assert seen["data"]["request_token"]=="request"
