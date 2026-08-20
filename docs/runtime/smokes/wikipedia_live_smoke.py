"""
wikipedia_live_smoke.py — live-network pilot for the [conn-15] Wikipedia
company-context connector.

This pilot hits the real Wikipedia REST API to verify the connector's
end-to-end behavior against the production endpoint. It is **network-
conditional** — most calls will FAIL behind the user's school network
(Securly sometimes blocks Wikipedia) or behind a VPN that redirects
DNS. The pilot marks such failures as `skipped` rather than `fail` so
the regression sweep doesn't break on a clean network.

Coverage (4 live tickers across 3 sectors):

  1. **summary()** — AAPL/NVDA/MSFT/JPM all return SUCCESS with title,
     description, extract, page_url, wikibase_item, and an ETag header.
  2. **ETag round-trip** — second call with the prior ETag returns
     status=UNCHANGED with the ETag echoed back.
  3. **resolve_ticker()** — AAPL/NVDA/BRK.B/JPM all resolve to a
     company-shaped Wikipedia page (corporate shape beats fruit/place
     disambiguation).
  4. **description_only()** — single-line blurb for NVDA.
  5. **sections()** — top-4 sections for NVDA with anchor + 1500-char
     text body each.

Run:

    PYTHONPATH=docs python3 docs/runtime/smokes/wikipedia_live_smoke.py

The pilot drops the standard HTTP_PROXY/HTTPS_PROXY env vars so a clean
network reaches Wikipedia; behind a proxy that hard-binds .wikipedia.org,
the connector surfaces FAILED with the underlying error and the pilot
marks the section `skipped`.
"""

from __future__ import annotations

import os
import sys

# Drop any proxy so a clean network reaches Wikipedia directly.
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(k, None)


_TOTAL = 0
_PASS = 0
_FAILED = 0
_SKIPPED = 0


def section(name: str) -> None:
    print(f"\n=== {name} ===")


def step(label: str, ok: bool, *, hint: str = "") -> None:
    global _TOTAL, _PASS, _FAILED
    _TOTAL += 1
    if ok:
        _PASS += 1
        print(f"  ok    | {label}")
    else:
        _FAILED += 1
        suffix = f"   <- {hint}" if hint else ""
        print(f"  FAIL  | {label}{suffix}")


def skip(label: str, reason: str) -> None:
    global _SKIPPED, _TOTAL
    _SKIPPED += 1
    _TOTAL += 1
    print(f"  skip  | {label}  ({reason})")


from runtime.tools.wikipedia import WikipediaTool  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. summary() — 4 tickers
# --------------------------------------------------------------------------- #
section("1. summary() — 4 live tickers")
tool = WikipediaTool()
test_set = [
    ("AAPL", "Apple Inc."),
    ("NVDA", "Nvidia"),
    ("MSFT", "Microsoft"),
    ("JPM", "JPMorgan Chase"),
]
first_success = None
for ticker, name in test_set:
    r = tool.summary(ticker, company_name=name)
    if r.status == "SUCCESS":
        if first_success is None:
            first_success = (ticker, r)
        d = r.data or {}
        step(
            f"{ticker:5}: SUCCESS, title={d.get('title')!r}, "
            f"description={d.get('description')!r}",
            True,
        )
        step(
            f"{ticker:5}: extract non-empty (≥100 chars)",
            len(d.get("extract") or "") >= 100,
        )
        step(
            f"{ticker:5}: page_url is en.wikipedia.org/wiki/*",
            (d.get("page_url") or "").startswith(
                "https://en.wikipedia.org/wiki/"),
        )
        step(
            f"{ticker:5}: wikibase_item present (Q*)",
            bool((d.get("wikibase_item") or "").startswith("Q")),
        )
        step(f"{ticker:5}: etag carried", bool(r.etag))
    else:
        skip(f"{ticker:5} (status={r.status})", r.note or "upstream unavailable")


# --------------------------------------------------------------------------- #
# 2. ETag round-trip — second call with prior ETag → UNCHANGED
# --------------------------------------------------------------------------- #
section("2. ETag round-trip")
if first_success is not None:
    ticker, r1 = first_success
    r2 = tool.summary(ticker, title=(r1.data or {}).get("title"),
                      if_none_match=r1.etag)
    step(
        f"second {ticker} summary with if_none_match → UNCHANGED",
        r2.status == "UNCHANGED",
    )
    step("UNCHANGED carries the prior ETag",
         (r2.etag or "") == (r1.etag or ""))
else:
    skip("ETag round-trip (no first SUCCESS to chain)", "all summaries FAILED")


# --------------------------------------------------------------------------- #
# 3. resolve_ticker() — 4 tickers, company-shaped
# --------------------------------------------------------------------------- #
section("3. resolve_ticker() — 4 live tickers")
for ticker, name in [
    ("AAPL", "Apple"),
    ("NVDA", "Nvidia"),
    ("BRK.B", "Berkshire"),
    ("JPM", "JPMorgan"),
]:
    r = tool.resolve_ticker(ticker, company_name=name)
    if r.status == "SUCCESS":
        title = (r.data or {}).get("title") or ""
        step(
            f"{ticker:5}: resolved to {title!r}",
            True,
        )
        step(
            f"{ticker:5}: page_url canonical",
            (r.data or {}).get("page_url")
            == f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
        )
    else:
        skip(f"{ticker:5} (status={r.status})", r.note or "upstream unavailable")


# --------------------------------------------------------------------------- #
# 4. description_only() — single-line blurb
# --------------------------------------------------------------------------- #
section("4. description_only() — NVDA")
r = tool.description_only("NVDA", company_name="Nvidia")
if r.status == "SUCCESS":
    desc = (r.data or {}).get("description") or ""
    step(f"description present: {desc!r}", bool(desc))
    step("description is short (≤30 words)", len(desc.split()) <= 30)
else:
    skip(f"description_only (status={r.status})", r.note or "upstream unavailable")


# --------------------------------------------------------------------------- #
# 5. sections() — top-4 sections for NVDA
# --------------------------------------------------------------------------- #
section("5. sections() — NVDA top-4 sections")
r = tool.sections("NVDA", company_name="Nvidia", max_sections=4)
if r.status == "SUCCESS":
    secs = (r.data or {}).get("sections") or []
    step(f"{len(secs)} sections returned (≤4)", 0 < len(secs) <= 4)
    step("each section has a title", all(s.get("title") for s in secs))
    step("each section has text (≥50 chars)",
         all(len(s.get("text") or "") >= 50 for s in secs))
    step("no <tag> characters leaked into text",
         all("<" not in (s.get("text") or "") for s in secs))
elif r.status == "EMPTY":
    skip("sections EMPTY (real page may have flat structure)",
         "real API returned no <h2>-level sections")
else:
    skip(f"sections (status={r.status})", r.note or "upstream unavailable")


# --------------------------------------------------------------------------- #
print()
print("=== pilot complete ===")
print(f"  {_PASS}/{_TOTAL} assertions passed, {_FAILED} failed, {_SKIPPED} skipped")
sys.exit(0 if _FAILED == 0 else 1)