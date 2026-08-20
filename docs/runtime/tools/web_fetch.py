# tools/web_fetch.py — Single-page → text extraction.
#
# Used by the orchestrator and senior-analyst when a primary citation URL appears in
# a memo (e.g. vendor press release, transcript host). The runtime fetches the page,
# strips boilerplate, returns the readable text + the URL + a timestamp.
from __future__ import annotations
import os
import re
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any

from . import ToolResult
from runtime.retry import runtime_http_opener, RetryPolicy as _retry_policy


@dataclass
class WebFetchTool:
    user_agent: str = "Labourious runtime/0.1"
    max_chars: int = 50000

    def fetch(self, url: str) -> ToolResult:
        as_of = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        req = urllib.request.Request(
            url, headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        )
        # Retry+backoff on transient HTTP failures (5xx, 429 with Retry-After,
        # connection blips, timeouts). The runtime layer is now resilient to user-
        # network blips without each tool having to reimplement the policy.
        opener = runtime_http_opener(retry_policy=_retry_policy())
        try:
            with opener(req, timeout=30) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            return ToolResult(status="FAILED", data=None, as_of=as_of,
                              source="web_fetch", note=f"HTTP {e.code}: {e.reason}")
        except Exception as e:
            return ToolResult(status="FAILED", data=None, as_of=as_of,
                              source="web_fetch", note=f"{type(e).__name__}: {e}")
        try:
            html = raw.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            html = raw.decode("latin-1", errors="replace")
        text = self._to_text(html)
        if len(text) > self.max_chars:
            text = text[: self.max_chars] + "...[truncated]"
        return ToolResult(status="SUCCESS", data={"text": text, "url": url}, as_of=as_of,
                          source="web_fetch", note=f"Fetched {len(text)} chars from {url}")

    def _to_text(self, html: str) -> str:
        # Strip <script> and <style>; collapse whitespace; preserve line breaks from <br>/<p>.
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<br[^>]*>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"</p\s*>", "\n\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()
