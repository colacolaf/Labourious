# tools/news.py — News layer. Default: Google News RSS (free, no key). Optional: NewsAPI.
from __future__ import annotations
import os
import json
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

from . import ToolResult


@dataclass
class NewsTool:
    provider: str = "google_rss"  # 'google_rss' | 'newsapi'
    api_key: str | None = None

    def __post_init__(self):
        if self.provider == "newsapi":
            self.api_key = self.api_key or os.environ.get("NEWSAPI_KEY")
            if not self.api_key:
                # graceful degrade to google_rss
                self.provider = "google_rss"

    def search_news(self, query: str, since: str | None = None,
                    until: str | None = None, limit: int = 20) -> ToolResult:
        as_of = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if self.provider == "google_rss":
            return self._google_rss(query, limit, as_of)
        if self.provider == "newsapi":
            return self._newsapi(query, since, until, limit, as_of)
        return ToolResult(status="FAILED", data=None, as_of=as_of, source="news",
                          note=f"unknown news provider: {self.provider}")

    # ---------------------------------------------------------------- #
    # Google News RSS — free, no key
    # ---------------------------------------------------------------- #
    def _google_rss(self, query: str, limit: int, as_of: str) -> ToolResult:
        from urllib.parse import quote
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={"User-Agent": "Labourious runtime/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                tree = ET.parse(r)
        except urllib.error.URLError as e:
            return ToolResult(status="FAILED", data=None, as_of=as_of, source="news.google_rss",
                              note=f"network error: {e}")
        items = []
        for item in tree.getroot().iter("item"):
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub = item.findtext("pubDate") or ""
            items.append({"title": title, "url": link, "published_at": pub, "source": "google_rss"})
            if len(items) >= limit:
                break
        return ToolResult(
            status="SUCCESS" if items else "EMPTY",
            data=items, as_of=as_of, source="news.google_rss",
            note=f"Google News RSS top {limit} for query '{query}'.",
        )

    # ---------------------------------------------------------------- #
    # NewsAPI — requires key
    # ---------------------------------------------------------------- #
    def _newsapi(self, query: str, since: str | None, until: str | None,
                 limit: int, as_of: str) -> ToolResult:
        url = "https://newsapi.org/v2/everything"
        params = {"q": query, "pageSize": limit, "apiKey": self.api_key}
        if since:
            params["from"] = since
        if until:
            params["to"] = until
        from urllib.parse import urlencode
        url = f"{url}?{urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Labourious runtime/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return ToolResult(status="FAILED", data=None, as_of=as_of, source="news.newsapi",
                              note=f"newsapi: {e.code}")
        articles = payload.get("articles", [])
        items = [
            {"title": a.get("title"), "url": a.get("url"),
             "published_at": a.get("publishedAt"), "source": "newsapi:" + str(a.get("source", {}).get("name"))}
            for a in articles
        ]
        return ToolResult(
            status="SUCCESS" if items else "EMPTY",
            data=items, as_of=as_of, source="news.newsapi",
            note=f"NewsAPI top {limit} for query '{query}'.",
        )
