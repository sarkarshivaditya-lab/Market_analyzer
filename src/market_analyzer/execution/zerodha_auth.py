"""Kite Connect authentication helpers.

API secrets and access tokens must remain server-side/environment-only.
"""
from __future__ import annotations

import hashlib
import os
from urllib.parse import urlencode

import requests


BASE_URL="https://api.kite.trade"
LOGIN_URL="https://kite.zerodha.com/connect/login"


def login_url(api_key: str | None = None, redirect_params: str | None = None) -> str:
    key=api_key or os.environ["KITE_API_KEY"]
    params={"v":"3","api_key":key}
    if redirect_params:
        params["redirect_params"]=redirect_params
    return f"{LOGIN_URL}?{urlencode(params)}"


def exchange_request_token(
    request_token: str,
    api_key: str | None = None,
    api_secret: str | None = None,
    timeout: float = 15.0,
) -> dict:
    key=api_key or os.environ["KITE_API_KEY"]
    secret=api_secret or os.environ["KITE_API_SECRET"]
    token=str(request_token).strip()
    if not token:
        raise ValueError("request_token must not be empty")
    checksum=hashlib.sha256(f"{key}{token}{secret}".encode()).hexdigest()
    response=requests.post(
        f"{BASE_URL}/session/token",
        headers={"X-Kite-Version":"3"},
        data={"api_key":key,"request_token":token,"checksum":checksum},
        timeout=float(timeout),
    )
    response.raise_for_status()
    payload=response.json()
    if payload.get("status")!="success":
        raise RuntimeError(payload.get("message","Kite authentication failed"))
    data=payload.get("data") or {}
    if not data.get("access_token"):
        raise RuntimeError("Kite authentication succeeded without an access_token")
    return data
