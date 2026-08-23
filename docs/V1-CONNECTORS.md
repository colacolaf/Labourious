# V1 Connector Schema — Single Source of Truth

> **Every connector's parameters, response shape, citation metadata, and
> status behavior in one document.** The runtime's `TOOL_REGISTRY` in
> `docs/runtime/call_tool.py` is the authoritative binding; this document
> is the human-readable catalog that mirrors it exactly.
>
> Companion docs:
> - `V1-PROTOCOL.md` — agent schemas & runtime contract
> - `docs/frontend/PROTOCOL.md` — event protocol
> - `docs/frontend/connectors_catalog.py` — canonical catalog driving
>   Settings panel + connector strip

---

## 1. Universal Response: `ToolResult`

Every connector returns a `ToolResult` dataclass (`docs/runtime/tools/__init__.py`):

| Field | Type | Always present? | Notes |
|---|---|---|---|
| `status` | `"SUCCESS" \| "PARTIAL" \| "FAILED" \| "EMPTY" \| "UNCHANGED"` | ✅ | |
| `data` | `Any` | ✅ | `list[dict]` for tabular, `dict` for single-row, `str` for prose, `None` when FAILED/EMPTY |
| `as_of` | `str` | ✅ | ISO 8601 (e.g. `"2026-08-23T18:09:26Z"`) |
| `source` | `str` | ✅ | e.g. `"yfinance"`, `"sec_edgar"`, `"wikipedia"` |
| `note` | `str` | ✅ | Human-readable summary (`"23 rows"`, `"CIK not found"`) |
| `snippet_path` | `str \| None` | | Absolute path to cached snippet in `.runs/<run_id>/snippets/` |
| `etag` | `str \| None` | | Upstream ETag for conditional GET / snippet cache |

### Status semantics

| Status | Meaning | `data` value |
|---|---|---|
| `SUCCESS` | Connector returned data | The payload |
| `PARTIAL` | Some rows, but incomplete or capped | Subset of data |
| `FAILED` | Network/auth/parse error | `None` |
| `EMPTY` | Query executed, zero results | `[]` or `None` |
| `UNCHANGED` | HTTP 304 — cached version current | `None` (snippet reused) |

---

## 2. Connector Registry

18 connectors registered in `TOOL_REGISTRY` (13 unique categories + 3 quant + 3 Finnhub extensions).
Grouped by tier from the connector catalog.

### 2.1 Tier 1 — Free / no key

---

#### `sec_edgar` — SEC EDGAR filings index

| | |
|---|---|
| **Tool ID** | `sec_edgar` |
| **Catalog name** | `sec_edgar` |
| **Provider** | `edgar_rest` |
| **Key required** | No |
| **Label** | SEC EDGAR |
| **Citation kind** | `sec_filing` |
| **Snippet-cacheable** | No |

**Default method:** `cik_for_ticker`

| Method | Parameters | Returns | Notes |
|---|---|---|---|
| `cik_for_ticker` | `ticker: str` | `str \| None` | Returns raw CIK string (e.g. `"0000320193"`); no ToolResult wrapper |
| `recent_filings` | `ticker`, `form="10-K"`, `limit=5` | `ToolResult` | `data` = `list[{accessionNumber, filingDate, form, primaryDocument}]` |

**Status paths:**
- `SUCCESS` — filings list returned
- `FAILED` — CIK not found, SSL cert error, HTTP timeout
- `EMPTY` — no filings of that form found

**Citation extraction:** `filingDate` + `form` + `primaryDocument` URL → chip

---

#### `sec_edgar_fulltext` — SEC full-text search (EFTS)

| | |
|---|---|
| **Tool ID** | `sec_edgar_fulltext` |
| **Catalog name** | `sec_edgar_fulltext` |
| **Provider** | `efts` |
| **Key required** | No |
| **Label** | SEC full-text search |
| **Snippet-cacheable** | Yes (TTL: 24 h) |

**Default method:** `search`

| Method | Parameters | Returns | Notes |
|---|---|---|---|
| `search` | `query`, `forms`, `ciks`, `start`, `end`, `limit`, `if_none_match` | `ToolResult` | Full-text across every filing since 2001 |

**Status paths:**
- `SUCCESS` — results returned; `data` = `list[{cik, company, form, filingDate, ...}]`
- `UNCHANGED` — HTTP 304, snippet cache preserved
- `FAILED` — SSL cert error, HTTP timeout
- `EMPTY` — no results for query

**Citation extraction:** `company` + `form` + `filingDate` → chip

---

#### `news_8k` — 8-K material-event wire

| | |
|---|---|
| **Tool ID** | `news_8k` |
| **Catalog name** | `news_8k` |
| **Provider** | `edgar_8k` |
| **Key required** | No |
| **Label** | 8-K wire |
| **Snippet-cacheable** | Yes (TTL: 1 h) |

**Default method:** `latest`

| Method | Parameters | Returns | Notes |
|---|---|---|---|
| `latest` | `ticker`, `since_days=7`, `items=None`, `limit=10`, `if_none_match` | `ToolResult` | |
| `material_only` | `ticker`, `since_days=30`, `items`, `limit`, `if_none_match` | `ToolResult` | Filters to Items 1.01–9.01 |
| `search` | `ticker`, `since_days`, `items`, `query`, `limit`, `if_none_match` | `ToolResult` | Keyword-filtered |

**Status paths:** `SUCCESS` / `UNCHANGED` / `FAILED` / `EMPTY`
**Data shape:** `list[{filingDate, items, description, url}]`
**Citation extraction:** `description` + `filingDate` + `url` → chip

---

#### `insider` — Insider transactions (Form 4)

| | |
|---|---|
| **Tool ID** | `insider` |
| **Catalog name** | `insider` |
| **Provider** | `openinsider` |
| **Key required** | No |
| **Label** | Insider (Form 4) |

**Default method:** `cluster_buys`

| Method | Parameters | Returns |
|---|---|---|
| `cluster_buys` | `ticker`, `since_days=90`, `kind="open-market"`, `min_value=50000`, `limit=20` | `ToolResult` |
| `ceo_cfo_buys` | `ticker`, `since_days=90` | `ToolResult` |

**Data shape:** `list[{filingDate, insider, title, tradeType, price, qty, value, ...}]`
**Citation extraction:** `insider` + `tradeType` + `filingDate` → chip

---

#### `institutional` — Institutional holdings (13F)

| | |
|---|---|
| **Tool ID** | `institutional` |
| **Catalog name** | `institutional` |
| **Provider** | `edgar_13f` |
| **Key required** | No |
| **Label** | Institutional (13F) |

**Default method:** `major_holders`

| Method | Parameters | Returns |
|---|---|---|
| `major_holders` | `ticker`, `since_quarters=4`, `limit=20` | `ToolResult` |

**Data shape:** `list[{filer, shares, value, change, filingDate}]`
**Citation extraction:** `filer` + `filingDate` → chip

---

#### `transcripts` — Earnings-call transcripts

| | |
|---|---|
| **Tool ID** | `transcripts` |
| **Catalog name** | `transcripts` |
| **Provider** | `seekingalpha_scrape` |
| **Key required** | No |
| **Label** | Earnings-call transcripts |
| **Snippet-cacheable** | Yes (TTL: 7 d) |

**Default method:** `list_for_ticker`

| Method | Parameters | Returns |
|---|---|---|
| `list_for_ticker` | `ticker`, `since_quarters=4`, `limit=10`, `if_none_match` | `ToolResult` |
| `fetch_transcript` | `ticker`, `transcript_id` | `ToolResult` |

**Data shape:** `list[{date, title, ticker, transcript_id, snippet}]` for list; raw text for fetch
**Citation extraction:** `title` + `date` → chip

---

#### `quotes` / `market_data` — OHLCV (yfinance)

| | |
|---|---|
| **Tool ID** | `market_data` |
| **Catalog name** | `quotes` |
| **Provider** | `yfinance` |
| **Key required** | No |
| **Label** | Quotes (yfinance) |
| **Citation kind** | `price` |

**Default method:** `price_history`

| Method | Parameters | Returns |
|---|---|---|
| `price_history` | `ticker`, `period="1y"`, `interval="1d"` | `ToolResult` |
| `fred_series` | `series_id`, `limit=100` | `ToolResult` (needs `FRED_API_KEY`) |

**Data shape (price_history):** `list[{date, Open, High, Low, Close, Volume}]`
**Real response confirmed:** AAPL 5d/1d → 5 rows, CSV-format OHLCV
**Citation extraction:** `date` + `Close` → chip

---

#### `news` — Google News RSS

| | |
|---|---|
| **Tool ID** | `news` |
| **Catalog name** | `news_rss` |
| **Provider** | `google_rss` |
| **Key required** | No |
| **Label** | News (Google RSS) |
| **Citation kind** | `news` |

**Default method:** `search_news`

| Method | Parameters | Returns |
|---|---|---|
| `search_news` | `query`, `limit=10` | `ToolResult` |

**Data shape:** `list[{title, url, source, published}]`
**Citation extraction:** `title` + `url` + `source` → chip

---

#### `web_fetch` — Generic web fetch

| | |
|---|---|
| **Tool ID** | `web_fetch` |
| **Catalog name** | `web_fetch` |
| **Provider** | `web_fetch` |
| **Key required** | No |
| **Label** | Generic web fetch |
| **Citation kind** | `web` |

**Default method:** `fetch`

| Method | Parameters | Returns |
|---|---|---|
| `fetch` | `url` | `ToolResult` |

**Data shape:** `str` (HTML → extracted text)
**Status paths:** `SUCCESS` / `FAILED` (HTTP error, timeout, SSL)
**Citation extraction:** The `url` itself → chip

---

#### `wikipedia` — Company context

| | |
|---|---|
| **Tool ID** | `wikipedia` |
| **Catalog name** | `wikipedia` (NEW, free Tier 4) |
| **Provider** | `wikipedia` |
| **Key required** | No |
| **Label** | Wikipedia |
| **Citation kind** | `web` |

**Default method:** `summary`

| Method | Parameters | Returns | Notes |
|---|---|---|---|
| `resolve_ticker` | `ticker`, `company_name` | `ToolResult` | Disambiguates ticker → page title |
| `summary` | `ticker`, `company_name`, `title`, `if_none_match` | `ToolResult` | Lead-section extract (≤200 words) |
| `sections` | `ticker`, `company_name`, `max_sections=8` | `ToolResult` | Top-of-page sections |
| `description_only` | `ticker`, `company_name` | `ToolResult` | ≤30 word one-liner |

**Data shape (summary):** `{title, extract, description, page_url, thumbnail, wikidata_id}`
**Real response confirmed:** AAPL → "Apple Inc. · American multinational technology company"
**Status paths:** `SUCCESS` / `EMPTY` (no company-shaped hit) / `FAILED` (network)
**Important:** Wikipedia is *narrative scaffolding*, not citable evidence per V2 prompt's [no-claim] protocol.

---

### 2.2 Tier 2 — Free with API key

---

#### `quotes_realtime` — Realtime quotes (Finnhub)

| | |
|---|---|
| **Tool ID** | `quotes_realtime` |
| **Catalog name** | `quotes_realtime` |
| **Provider** | `finnhub` |
| **Key env** | `FINNHUB_API_KEY` |
| **Rate limit** | 60 req/min (shared pool) |
| **Default method:** `quote` |

| Method | Parameters | Returns |
|---|---|---|
| `quote` | `ticker`, `resolution="D"`, `days_back=5`, `limit=100` | `ToolResult` |

**Data shape:** `{current, high, low, open, prevClose, t, change, changePercent, candles[]}`
**Status:** `SUCCESS` / `FAILED` (key missing, auth error, rate limit) / `EMPTY`

---

#### `fundamentals` — Financials (FMP)

| | |
|---|---|
| **Tool ID** | `fundamentals` |
| **Catalog name** | `fundamentals` |
| **Provider** | `fmp` |
| **Key env** | `FMP_API_KEY` |
| **Rate limit** | 250 req/day |
| **Default method:** `income_statement` |

| Method | Parameters | Returns |
|---|---|---|
| `income_statement` | `ticker`, `period="annual"`, `limit=5` | `ToolResult` |
| `balance_sheet` | `ticker`, `period="annual"`, `limit=5` | `ToolResult` |
| `cash_flow` | `ticker`, `period="annual"`, `limit=5` | `ToolResult` |
| `key_metrics` | `ticker`, `period="annual"`, `limit=5` | `ToolResult` |
| `ratios` | `ticker`, `period="annual"`, `limit=5` | `ToolResult` |

**Data shape:** `list[{date, ...financial fields}]` (varies by method)
**Status:** `SUCCESS` / `FAILED` / `EMPTY`

---

#### `consensus` — Sell-side consensus (Finnhub)

| | |
|---|---|
| **Tool ID** | `consensus` |
| **Catalog name** | `consensus` |
| **Provider** | `finnhub` |
| **Key env** | `FINNHUB_API_KEY` |
| **Default method:** `price_target` |

| Method | Parameters | Returns |
|---|---|---|
| `price_target` | `ticker` | `ToolResult` |
| `recommendations` | `ticker` | `ToolResult` |
| `revenue_estimate` | `ticker`, `freq="quarterly"`, `limit=10` | `ToolResult` |

**Data shape (price_target):** `{target_mean, target_high, target_low, number_analysts, ...}`

---

#### `calendars` — Earnings + IPO calendar (Finnhub)

| | |
|---|---|
| **Tool ID** | `calendars` |
| **Catalog name** | `calendars` |
| **Provider** | `finnhub` |
| **Key env** | `FINNHUB_API_KEY` |
| **Default method:** `earnings` |

| Method | Parameters | Returns |
|---|---|---|
| `earnings` | `ticker`, `start`, `end` | `ToolResult` |
| `ipo` | `start`, `end` | `ToolResult` |

**Data shape:** `list[{date, symbol, ...}]`

---

#### `newsapi` — News article search (NewsAPI.org)

| | |
|---|---|
| **Tool ID** | `newsapi` |
| **Catalog name** | `newsapi` |
| **Provider** | `newsapi` |
| **Key env** | `NEWSAPI_KEY` |
| **Rate limit** | 100 req/day |
| **Default method:** `everything` |

| Method | Parameters | Returns |
|---|---|---|
| `everything` | `query`, `since`, `until`, `sources`, `language`, `sort_by`, `limit` | `ToolResult` |
| `top_headlines` | `query`, `sources`, `country`, `category`, `limit` | `ToolResult` |
| `sources` | `category`, `language`, `country` | `ToolResult` |

**Data shape:** `list[{title, url, source, publishedAt, description}]`

---

#### `macro` — Macro series (FRED)

| | |
|---|---|
| **Tool ID** | `macro` |
| **Catalog name** | `macro` |
| **Provider** | `fred` |
| **Key env** | `FRED_API_KEY` |
| **Rate limit** | 120 req/min |
| **Default method:** `series` |

| Method | Parameters | Returns |
|---|---|---|
| `series` | `series_id`, `limit=100`, `sort_order="desc"`, `query` | `ToolResult` |
| `search` | `query`, `limit=20` | `ToolResult` |
| `release_calendar` | `limit=20` | `ToolResult` |

**Data shape:** `list[{date, value}]` for series; `list[{id, title, frequency, ...}]` for search

---

### 2.3 Tier 3 — Paid / specialty

---

#### `options_chain` — Options chain (Finnhub)

| | |
|---|---|
| **Tool ID** | `options_chain` |
| **Provider** | `finnhub` |
| **Key env** | `FINNHUB_API_KEY` |
| **Default method:** `chain` |

| Method | Parameters | Returns |
|---|---|---|
| `chain` | `ticker`, `expiration`, `limit` | `ToolResult` |
| `expirations` | `ticker` | `ToolResult` |

**Data shape:** `list[{strike, expiration, type, last, bid, ask, volume, oi, iv, delta, gamma, ...}]`

---

#### `short_interest` — Short interest (Finnhub)

| | |
|---|---|
| **Tool ID** | `short_interest` |
| **Provider** | `finnhub` |
| **Key env** | `FINNHUB_API_KEY` |
| **Default method:** `history` |

| Method | Parameters | Returns |
|---|---|---|
| `history` | `ticker`, `from_date`, `to_date` | `ToolResult` |
| `latest` | `ticker` | `ToolResult` |

**Data shape:** `list[{settlementDate, shortInterest, avgDailyShareVolume, daysToCover, is_squeeze_candidate}]`
**Derived field:** `is_squeeze_candidate` (>20% float short AND >3 days to cover)

---

#### `sentiment_social` — Social sentiment (Stocktwits)

| | |
|---|---|
| **Tool ID** | `sentiment_social` |
| **Provider** | `stocktwits` |
| **Key required** | No (public stream) |
| **Default method:** `messages` |

| Method | Parameters | Returns |
|---|---|---|
| `messages` | `ticker`, `limit=30`, `top_n=5` | `ToolResult` |
| `trending` | | `ToolResult` |

**Data shape:** `{total, bullish, bearish, messages: [{body, created_at, sentiment, user}]}`

---

### 2.4 Quant tools (deterministic, no LLM)

---

#### `quant_dcf` — Discounted Cash Flow

| | |
|---|---|
| **Tool ID** | `quant_dcf` |
| **Default method:** `run_model` |
| **Passes request:** Yes |

| Parameter | Type | Notes |
|---|---|---|
| `request` | `dict` | `{ticker, growth_rate?, discount_rate?, terminal_growth?, years?}` |

**Data shape:** `{ticker, per_share, assumptions, ...}`
**Status:** `SUCCESS` / `FAILED` (if fundamentals unavailable or math errors out)

---

#### `quant_comps` — Comparable Company Analysis

| | |
|---|---|
| **Tool ID** | `quant_comps` |
| **Default method:** `run` |
| **Passes request:** Yes |

| Parameter | Type | Notes |
|---|---|---|
| `request` | `dict` | `{subject: {ticker}, peers: [{ticker}, ...], metric?, period?}` |

**Data shape:** `list[{ticker, metric_value, ...}]` with subject + peer rows
**Status:** `SUCCESS` / `PARTIAL` (some peers failed) / `FAILED`

---

#### `quant_comparator` — Heuristic Comparator

| | |
|---|---|
| **Tool ID** | `quant_comparator` |
| **Default method:** `run` |

| Parameter | Type | Notes |
|---|---|---|
| `rubric` | `dict` | `{dimensions: [{name, weight, higher_is_better, ...}], candidates: [{ticker, values: {dim: score}}]}` |

**Data shape:** `{scores: [{ticker, total, dimension_scores}], winner, confidence}`
**Status:** `SUCCESS` / `FAILED` (matrix degenerate or empty)

---

## 3. Snippet Cache Pipeline

Three connectors are snippet-cacheable — the runtime writes the first 2 KB of `ToolResult.data`
to `.runs/<run_id>/snippets/<source>_<idx>.txt` on SUCCESS, with TTL-gated refresh:

| Connector | TTL | Rationale |
|---|---|---|
| `news_8k` | 1 hour | 8-Ks are time-sensitive — material events can update within an hour |
| `sec_edgar_fulltext` | 24 hours | Amendments settle within a day |
| `transcripts` | 7 days | Call transcripts only refresh Q-on-Q |

**Refresh triggers (both must agree to skip):**
1. TTL gate: `now - written_at >= ttl_seconds`
2. As-of gate: `ToolResult.as_of > cached.cached_as_of` (newer upstream data)

**ETag short-circuit:** When upstream returns HTTP 304 `UNCHANGED`, snippet cache preserves
content byte-for-byte regardless of TTL/as-of. Zero body bytes downloaded.

See `docs/runtime/snippets.py` for the full implementation.

---

## 4. Real Response Verification

Tested 2026-08-23 against the actual Python connectors in this environment:

| Connector | Method | Status | Notes |
|---|---|---|---|
| `market_data` | `price_history("AAPL", "5d", "1d")` | ✅ SUCCESS | 5 rows, real OHLCV from yfinance |
| `wikipedia` | `description_only("AAPL")` | ✅ SUCCESS | "Apple Inc. · American multinational technology company" |
| `wikipedia` | `summary("NVDA")` | ✅ SUCCESS | Disambiguated to PHLX Semiconductor Sector (NVDA → SOX index, not ticker) |
| `sec_edgar` | `cik_for_ticker("AAPL")` | ❌ SSL block | Securly MITM intercept — `CERTIFICATE_VERIFY_FAILED`. Works off-network. |

---

## 5. Adding a New Connector

1. **Implement the tool class** in `docs/runtime/tools/<name>.py` with a `ToolResult`-returning method.
2. **Register it** in `docs/runtime/call_tool.py` → `TOOL_REGISTRY` with a `ToolBinding`.
3. **Add to the catalog** in `docs/frontend/connectors_catalog.py` → `ALL_CONNECTORS`.
4. **Wire the import** in `docs/runtime/call_tool.py` top-of-file.
5. **Smoke-test** via `PYTHONPATH=docs python3 -c "from runtime.call_tool import call_tool; ..."`.
6. **Update this document** with the new connector's schema.

No TUI changes needed — the connector strip and Settings panel read the catalog directly.

---

*Maintained alongside `docs/runtime/call_tool.py`'s `TOOL_REGISTRY`. When you add a connector, update this document.*