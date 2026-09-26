#!/usr/bin/env python3
"""Interactive one-time Kite Connect login helper."""
import getpass
import os

from market_analyzer.execution.zerodha_auth import exchange_request_token, login_url


def main():
    api_key=os.environ.get("KITE_API_KEY")
    if not api_key:
        raise SystemExit("Set KITE_API_KEY first.")
    print("Open this URL in your browser:")
    print(login_url(api_key))
    print()
    print("After successful Zerodha login, copy the request_token from the redirect URL.")
    request_token=input("request_token: ").strip()
    data=exchange_request_token(request_token,api_key=api_key,api_secret=os.environ.get("KITE_API_SECRET") or getpass.getpass("KITE_API_SECRET: "))
    print(f"Authenticated as {data.get('user_name') or data.get('user_id')}.")
    print("Access token received. It is valid only for the current daily session.")
    print("Export KITE_ACCESS_TOKEN in this shell; do not commit it to Git.")


if __name__=="__main__":
    main()
