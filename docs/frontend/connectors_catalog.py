"""
connectors_catalog.py — the canonical catalog of supported financial data connectors.

9 entries, organized by tier:
  Tier 1 — Free / no key (ship first; primary discovery backbone)
  Tier 2 — Free with API key (5-line signup, 60/day on the lowest tier)
  Tier 3 — Paid / specialty (requires subscription; defer)

The catalog drives:
  - The default connector list in the Settings → Connectors panel
  - The KEY-required indicator + KEY env-var name on each row
  - The "what fired during this flow" ribbon under each agent bubble
  - The "active / stale" counter in the chat footer

Curated list lives in `docs/CONNECTORS.md` — every entry below is research-backed
(Kang/Liu 2023; Anthropic multi-agent paper 2025; Toolformer 2023; Ant Group RLFKV
2026; CFA Institute 2024). The catalog is the single source of truth that the
runtime + TUI + config_io all import from.

Tier semantics:
  tier="free"      keyless or key-only; default ON; ships with the build
  tier="tier1"     alias of "free" — kept separate for legacy scripts
  tier="tier2"     free-with-key, default ON, requires one-time API key entry
  tier="tier3"     paid, default OFF; user opts in
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ConnectorTier = Literal["free", "tier1", "tier2", "tier3"]


@dataclass(frozen=True)
class ConnectorEntry:
    """One connector — single source of truth for name + tier + key metadata."""
    name: str             # canonical id used in config_io + tool runtime
    label: str            # human-readable for settings panel (long form)
    short: str            # human-readable for inline strip (≤ 10 chars)
    provider: str         # underlying tool / provider name (e.g. "edgar_rest", "yfinance")
    tier: ConnectorTier
    key_env: str | None   # env var name when key required; None for keyless
    keyless: bool         # shortcut for "no key needed"
    description: str      # 1-line for the row tooltip
    citation_kind: str    # how citations from this source render in citation_chip
    default_on: bool      # ship-on default
    recommended: bool     # include in the MVP-5 set


# ----------------------------------------------------------- catalog
ALL_CONNECTORS: tuple[ConnectorEntry, ...] = (
    # ----- Tier 1 — Free / no key (MVP backbone) -----
    ConnectorEntry(
        name="sec_edgar",
        label="SEC EDGAR",
        short="EDGAR",
        provider="edgar_rest",
        tier="free",
        key_env=None,
        keyless=True,
        description="Primary filings index (10-K, 10-Q, 8-K, DEF 14A) — auditor-grade.",
        citation_kind="sec_filing",
        default_on=True,
        recommended=True,
    ),
    ConnectorEntry(
        name="sec_edgar_fulltext",
        label="SEC full-text search",
        short="EFTS",
        provider="efts",
        tier="free",
        key_env=None,
        keyless=True,
        description="EFTS query across every filing since 2001 — the missing primary-discovery layer.",
        citation_kind="sec_filing",
        default_on=True,
        recommended=True,
    ),
    ConnectorEntry(
        name="quotes",
        label="Quotes (yfinance)",
        short="quotes",
        provider="yfinance",
        tier="free",
        key_env=None,
        keyless=True,
        description="Delayed OHLCV + options chain + short interest via yfinance. 15-min delay.",
        citation_kind="price",
        default_on=True,
        recommended=True,
    ),
    ConnectorEntry(
        name="quotes_realtime",
        label="Realtime quotes (Finnhub)",
        short="Finnhub",
        provider="finnhub",
        tier="tier2",
        key_env="FINNHUB_API_KEY",
        keyless=False,
        description="Finnhub /quote + /stock/candle — free w/ key, 60 req/min. Realtime price + OHLCV from 1m to 1d.",
        citation_kind="price",
        default_on=False,
        recommended=True,
    ),
    ConnectorEntry(
        name="fundamentals",
        label="Fundamentals (Financial Modeling Prep)",
        short="FMP",
        provider="fmp",
        tier="tier2",
        key_env="FMP_API_KEY",
        keyless=False,
        description="FMP /stable router — income statement, balance sheet, cash flow, key metrics, ratios. Free w/ key, 250 req/day.",
        citation_kind="filing",
        default_on=False,
        recommended=True,
    ),
    ConnectorEntry(
        name="consensus",
        label="Sell-side consensus (Finnhub)",
        short="consensus",
        provider="finnhub",
        tier="tier2",
        key_env="FINNHUB_API_KEY",
        keyless=False,
        description="Finnhub analyst consensus — price target, recommendations distribution (4 mo), revenue estimates (quarterly/annual). Free w/ key, same 60 req/min pool as quotes_realtime.",
        citation_kind="consensus",
        default_on=False,
        recommended=True,
    ),
    ConnectorEntry(
        name="calendars",
        label="Earnings + IPO calendar (Finnhub)",
        short="calendar",
        provider="finnhub",
        tier="tier2",
        key_env="FINNHUB_API_KEY",
        keyless=False,
        description="Finnhub /calendar/earnings + /calendar/ipo — upcoming prints and IPOs over a date window. Free w/ key, same 60 req/min pool.",
        citation_kind="calendar",
        default_on=False,
        recommended=True,
    ),
    ConnectorEntry(
        name="newsapi",
        label="News articles (NewsAPI.org)",
        short="NewsAPI",
        provider="newsapi",
        tier="tier2",
        key_env="NEWSAPI_KEY",
        keyless=False,
        description="NewsAPI.org /v2/everything + /v2/top-headlines + /v2/sources — structured article search across the indexed news corpus. Free w/ key, 100 req/day.",
        citation_kind="news",
        default_on=False,
        recommended=True,
    ),
    ConnectorEntry(
        name="macro",
        label="Macro series (FRED)",
        short="FRED",
        provider="fred",
        tier="tier2",
        key_env="FRED_API_KEY",
        keyless=False,
        description="Federal Reserve Economic Data — series lookup, catalog search, upcoming release calendar. Free w/ key, 120 req/min no-quota dev tier.",
        citation_kind="macro",
        default_on=False,
        recommended=True,
    ),
    ConnectorEntry(
        name="options_chain",
        label="Options chain (Finnhub)",
        short="chain",
        provider="finnhub",
        tier="tier3",
        key_env="FINNHUB_API_KEY",
        keyless=False,
        description="Finnhub /stock/option-chain + /stock/option-expiry-dates — full options chain (greeks, OI, IV, bid/ask) per strike per expiry. Free w/ key, same 60 req/min pool as quotes_realtime/consensus/calendars.",
        citation_kind="options",
        default_on=False,
        recommended=True,
    ),
    ConnectorEntry(
        name="short_interest",
        label="Short interest (Finnhub)",
        short="shorts",
        provider="finnhub",
        tier="tier3",
        key_env="FINNHUB_API_KEY",
        keyless=False,
        description="Finnhub /stock/short-interest — FINRA biweekly short-interest rows. Derived is_squeeze_candidate flag (>20 % float short AND >3 days to cover). Same key as the rest of the Finnhub pool.",
        citation_kind="short_interest",
        default_on=False,
        recommended=True,
    ),
    ConnectorEntry(
        name="sentiment_social",
        label="Social sentiment (Stocktwits)",
        short="Stocktwits",
        provider="stocktwits",
        tier="tier3",
        key_env=None,
        keyless=True,
        description="Stocktwits public stream — per-symbol recent messages + self-tagged Bullish/Bearish counts + trending equities. No auth required. Read-only; sends a polite UA. Snapshot-of-now (no historical pagination).",
        citation_kind="social",
        default_on=False,
        recommended=True,
    ),
    ConnectorEntry(
        name="news_rss",
        label="News (Google RSS)",
        short="news",
        provider="google_rss",
        tier="free",
        key_env=None,
        keyless=True,
        description="Google News RSS — cheap headline discovery across all topics.",
        citation_kind="news",
        default_on=True,
        recommended=True,
    ),
    ConnectorEntry(
        name="news_8k",
        label="8-K wire",
        short="8-K",
        provider="edgar_8k",
        tier="free",
        key_env=None,
        keyless=True,
        description="SEC 8-K filings — the legally-mandated material-event wire.",
        citation_kind="sec_filing",
        default_on=True,
        recommended=True,
    ),
    ConnectorEntry(
        name="insider",
        label="Insider (Form 4)",
        short="insider",
        provider="openinsider",
        tier="free",
        key_env=None,
        keyless=True,
        description="Cluster buys + CEO/CFO direct buys = the most-cited insider signal.",
        citation_kind="insider",
        default_on=True,
        recommended=True,
    ),
    ConnectorEntry(
        name="institutional",
        label="Institutional (13F)",
        short="13F",
        provider="edgar_13f",
        tier="free",
        key_env=None,
        keyless=True,
        description="Quarterly 13F-HR smart-money positions — second-most-cited signal.",
        citation_kind="filing",
        default_on=False,
        recommended=False,
    ),
    ConnectorEntry(
        name="transcripts",
        label="Earnings-call transcripts",
        short="trans.",
        provider="seekingalpha_scrape",
        tier="free",
        key_env=None,
        keyless=True,
        description="SeekingAlpha earnings-call transcripts (cached on first pull).",
        citation_kind="transcript",
        default_on=False,
        recommended=False,
    ),
    ConnectorEntry(
        name="web_fetch",
        label="Generic web fetch",
        short="web",
        provider="web_fetch",
        tier="free",
        key_env=None,
        keyless=True,
        description="Generic HTML → text. Used when the orchestrator cites a non-canonical URL.",
        citation_kind="web",
        default_on=True,
        recommended=True,
    ),
)


def by_name(name: str) -> ConnectorEntry | None:
    """Look up a connector entry by canonical name. None when unknown."""
    for c in ALL_CONNECTORS:
        if c.name == name:
            return c
    return None


def by_tier(tier: ConnectorTier) -> tuple[ConnectorEntry, ...]:
    """Filter catalog by tier ('free' / 'tier1' / 'tier2' / 'tier3')."""
    if tier == "tier1":
        tier = "free"  # tier1 is an alias for free in the catalog
    return tuple(c for c in ALL_CONNECTORS if c.tier == tier)


TIER_ORDER = ("free", "tier2", "tier3")
TIER_LABEL = {
    "free":  "free · no key",
    "tier2": "free · key req.",
    "tier3": "paid",
}


def key_required_count() -> int:
    """Number of connectors that need any kind of API key."""
    return sum(0 if c.keyless else 1 for c in ALL_CONNECTORS)


def recommended() -> tuple[ConnectorEntry, ...]:
    """The MVP-5 set: connectors that ship on by default — the recommended backbone."""
    return tuple(c for c in ALL_CONNECTORS if c.recommended and c.default_on)
