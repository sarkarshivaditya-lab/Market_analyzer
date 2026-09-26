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

_POSITIVE={"beat","growth","upgrade","strong","profit","surge","record","bullish","positive"}
_NEGATIVE={"miss","loss","downgrade","weak","fraud","fall","drop","bearish","negative","warning"}

def title_sentiment(title:str)->float:
    words={w.strip(".,:;!?()[]").lower() for w in title.split()}
    score=len(words&_POSITIVE)-len(words&_NEGATIVE)
    return float(max(-1.0,min(1.0,score/3.0)))

class RssNewsProvider:
    """Timestamped RSS ingestion for live context; not a substitute for historical news archives."""
    def __init__(self,feeds:dict[str,str]):
        self.feeds=feeds
    def fetch(self,tickers:list[str],as_of:pd.Timestamp|None=None)->list[NewsItem]:
        if as_of is None:
            cutoff=None
        else:
            cutoff=pd.Timestamp(as_of)
            cutoff=cutoff.tz_localize("UTC") if cutoff.tzinfo is None else cutoff.tz_convert("UTC")
        items=[]
        for ticker in tickers:
            url=self.feeds.get(ticker)
            if not url: continue
            request=Request(url,headers={"User-Agent":"market-analyzer/0.1"})
            root=ET.fromstring(urlopen(request,timeout=15).read())
            for item in root.findall(".//item"):
                title=item.findtext("title") or ""
                link=item.findtext("link") or ""
                published=item.findtext("pubDate") or ""
                if not published: continue
                ts=pd.Timestamp(parsedate_to_datetime(published)).tz_convert("UTC")
                if cutoff is not None and ts>cutoff: continue
                items.append(NewsItem(ticker,ts,"rss",title,link,title_sentiment(title)))
        return sorted(items,key=lambda x:x.published_at)

def aggregate_news(items:list[NewsItem])->pd.DataFrame:
    if not items:
        return pd.DataFrame(columns=["date","tic","news_count","news_sentiment","news_count_3d","news_count_7d","news_sentiment_3d","news_sentiment_7d"])
    rows=[{"date":x.published_at.normalize(),"tic":x.ticker,"sentiment":x.sentiment} for x in items]
    frame=pd.DataFrame(rows).sort_values(["tic","date"])
    daily=frame.groupby(["date","tic"],as_index=False).agg(news_count=("sentiment","size"),news_sentiment=("sentiment","mean"))
    pieces=[]
    for tic,group in daily.groupby("tic",sort=False):
        group=group.sort_values("date").set_index("date")
        count=group["news_count"]
        weighted=group["news_sentiment"]*count
        group["news_count_3d"]=count.rolling("3D",closed="right").sum()
        group["news_count_7d"]=count.rolling("7D",closed="right").sum()
        group["news_sentiment_3d"]=weighted.rolling("3D",closed="right").sum()/group["news_count_3d"].replace(0,pd.NA)
        group["news_sentiment_7d"]=weighted.rolling("7D",closed="right").sum()/group["news_count_7d"].replace(0,pd.NA)
        group=group.reset_index()
        group["tic"]=tic
        pieces.append(group)
    out=pd.concat(pieces,ignore_index=True)
    out["date"]=pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out.sort_values(["date","tic"]).reset_index(drop=True)
