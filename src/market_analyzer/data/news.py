from __future__ import annotations

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

import pandas as pd


@dataclass(frozen=True)
class NewsItem:
    ticker: str
    published_at: pd.Timestamp
    source: str
    title: str
    url: str
    sentiment: float


_POSITIVE = {"beat", "growth", "upgrade", "strong", "profit", "surge", "record", "bullish", "positive"}
_NEGATIVE = {"miss", "loss", "downgrade", "weak", "fraud", "fall", "drop", "bearish", "negative", "warning"}


def title_sentiment(title: str) -> float:
    words = {w.strip(".,:;!?()[]").lower() for w in title.split()}
    score = len(words & _POSITIVE) - len(words & _NEGATIVE)
    return float(max(-1.0, min(1.0, score / 3.0)))


class RssNewsProvider:
    """Timestamped RSS ingestion for live context; not a substitute for historical news archives."""

    def __init__(self, feeds: dict[str, str]):
        self.feeds = feeds

    def fetch(self, tickers: list[str], as_of: pd.Timestamp | None = None) -> list[NewsItem]:
        cutoff = pd.Timestamp(as_of, tz="UTC") if as_of is not None and pd.Timestamp(as_of).tzinfo is None else pd.Timestamp(as_of).tz_convert("UTC") if as_of is not None else None
        items = []
        for ticker in tickers:
            url = self.feeds.get(ticker)
            if not url:
                continue
            request = Request(url, headers={"User-Agent": "market-analyzer/0.1"})
            root = ET.fromstring(urlopen(request, timeout=15).read())
            for item in root.findall(".//item"):
                title = item.findtext("title") or ""
                link = item.findtext("link") or ""
                published = item.findtext("pubDate") or ""
                if not published:
                    continue
                ts = pd.Timestamp(parsedate_to_datetime(published)).tz_convert("UTC")
                if cutoff is not None and ts > cutoff:
                    continue
                items.append(NewsItem(ticker, ts, "rss", title, link, title_sentiment(title)))
        return sorted(items, key=lambda x: x.published_at)


def aggregate_news(items: list[NewsItem]) -> pd.DataFrame:
    if not items:
        return pd.DataFrame(columns=["date", "tic", "news_count", "news_sentiment"])
    rows = [{"date": x.published_at.normalize(), "tic": x.ticker, "sentiment": x.sentiment} for x in items]
    frame = pd.DataFrame(rows)
    return frame.groupby(["date", "tic"], as_index=False).agg(
        news_count=("sentiment", "size"), news_sentiment=("sentiment", "mean")
    )
