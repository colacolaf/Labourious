# CONNECTORS-AUDIT — what the app needs, what exists, what's missing

> The app's agent-library nodes (technical, quant, macro, flow-and-transcript) each consume specific connectors. The app's custom-canvas model also *opens the gates* that `docs/DEFERRED.md` set for several deferred leads (sentiment, altdata, options-flow) — because the canvas lets a user *add* an agent to any graph, the "Re-hire if a flow needs X" gates are now trivially satisfiable.

This file audits: (1) what connectors exist today (22 total, per `docs/V1-CONNECTORS.md`), (2) what the app's agent-library nodes need, (3) the gaps, and (4) the recommended additions with research-backed reasoning.

Read this alongside `docs/V1-CONNECTORS.md` (the canonical connector schema) and `app/docs/AGENT-LIBRARY.md` (the catalog of agent nodes).

---

## 1. What exists today — the 22-connector inventory

From `docs/V1-CONNECTORS.md` and `docs/runtime/tools/`:

### Tier 1 — Free, no key (10 connectors)

| Tool ID | Source | What it returns | App usage |
|---|---|---|---|
| `sec_edgar` | SEC EDGAR REST | CIK + recent filings list | senior-analyst pre-flight (existing) |
| `sec_edgar_fulltext` | SEC EFTS | Full-text search across all filings since 2001 | forensic-accounting deep-dive |
| `news_8k` | SEC EDGAR 8-K | Material-event wire (1h TTL snippet cache) | senior-analyst pre-flight |
| `insider` | OpenInsider scrape | Form 4 cluster buys, CEO/CFO buys | **flow-and-transcript agent** |
| `institutional` | EDGAR 13F HTML parse | Major holders, quarterly changes | macro context |
| `transcripts` | Seeking Alpha scrape | Earnings-call transcripts (7d TTL) | **flow-and-transcript agent** |
| `market_data` | yfinance | OHLCV (daily/intraday) | **technical agent**, **macro agent** |
| `news` | Google News RSS | News headlines + URLs | senior-analyst pre-flight |
| `web_fetch` | generic | URL → extracted text | citation verification |
| `wikipedia` | Wikipedia REST | Company summary / sections | narrative scaffolding (non-citable) |

### Tier 2 — Free with API key (6 connectors)

| Tool ID | Source | Key env | What it returns |
|---|---|---|---|
| `quotes_realtime` | Finnhub | `FINNHUB_API_KEY` | Realtime quote (60 req/min free) |
| `fundamentals` | FMP | `FMP_API_KEY` | Income / balance / cashflow / key metrics / ratios (250 req/day) |
| `consensus` | Finnhub | `FINNHUB_API_KEY` | Price targets, recommendations, revenue estimates |
| `calendars` | Finnhub | `FINNHUB_API_KEY` | Earnings + IPO calendar |
| `newsapi` | NewsAPI.org | `NEWSAPI_KEY` | Article search (100 req/day) |
| `macro` | FRED | `FRED_API_KEY` | Macro time series (120 req/min) |

### Tier 3 — Paid / specialty (3 connectors)

| Tool ID | Source | What it returns |
|---|---|---|
| `options_chain` | Finnhub | Options chain + Greeks |
| `short_interest` | Finnhub | Short interest history + squeeze-candidate flag |
| `sentiment_social` | Stocktwits | Social sentiment (bullish/bearish message stream) |

### Tier 4 — Quant tools, deterministic, no LLM (3 connectors)

| Tool ID | What it does |
|---|---|
| `quant_dcf` | Discounted cash flow model |
| `quant_comps` | Comparable company analysis |
| `quant_comparator` | Heuristic multi-dimension comparator |

---

## 2. What the app's agent-library nodes need

From `app/docs/AGENT-LIBRARY.md`:

| Agent node | `connectors_consumed` (claimed) | What it actually needs |
|---|---|---|
| **Technical** | `["market_data"]` | Raw OHLCV **+ computed indicators** (RSI, MACD, MA, volume profile). Gap: indicators aren't a connector — see §3.1. |
| **Quant** | `["quant_dcf", "quant_comps", "quant_comparator"]` | All three exist. **No gap.** |
| **Macro** | `["market_data"]` + FRED separately | OHLCV + macro series. The `macro` connector exists (FRED). **No gap** — but `AGENT-LIBRARY.md` should list `macro` explicitly. |
| **Flow-and-transcript** | `["insider", "transcripts"]` | Both exist. **Fragility gap** — `insider` (OpenInsider scrape) and `institutional` (13F HTML) break on upstream changes. See §3.2. |
| **Research-forcer** | `[]` | None — it's a directive-injector, not a data consumer. **No gap.** |

---

## 3. The gaps — and the recommended fix for each

### 3.1 The indicators gap — Technical agent needs RSI/MACD/MA, not just raw OHLCV

**The problem:** The Technical agent claims to consume `market_data` and produce "RSI, MACD, momentum, volume profile" — but `market_data` returns raw OHLCV rows. The indicators must be computed somewhere.

**Research (2026-08-24):**

| Option | Stack | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A. Local compute via `pandas-ta`** | `pip install pandas-ta`; compute RSI/MACD/MA/VWAP from OHLCV in Python | Free, no key, no network call, deterministic, 130+ indicators | Adds a dep; CPU cost is trivial (microseconds per indicator) | **Chosen** |
| B. TAAPI.IO API | REST API, 200+ indicators, free tier | No compute on our side | Rate-limited (free tier ~1 req/s); network dependency; another key to manage; paid for commercial use | Rejected — adds a key + network dep for what local compute does better |
| C. FMP technical-indicators endpoint | `fundamentals` connector's provider has `/technical-indicator` | Already have FMP key | 250 req/day cap shared with fundamentals; indicators are a small subset | Rejected — competes with fundamentals for the same rate-limit budget |

**Fix:** Add a new **deterministic quant connector** `quant_indicators` (sibling to `quant_dcf` / `quant_comps` / `quant_comparator`) that wraps `pandas-ta`. It takes OHLCV (from `market_data` or passed in) + a list of indicator names, returns a `ToolResult` with the computed series. No key, no network, deterministic. Update the Technical agent's `connectors_consumed` to `["market_data", "quant_indicators"]`.

**File:** `docs/runtime/tools/indicators.py` (~150 lines). Register in `TOOL_REGISTRY`. Add to `ALL_CONNECTORS` in the catalog.

### 3.2 The fragility gap — `insider` and `institutional` rely on HTML scraping

**The problem:** `insider` (OpenInsider) and `institutional` (EDGAR 13F HTML) scrape HTML. When the upstream changes its markup, the connector breaks silently (returns `FAILED`). The Flow-and-transcript agent depends on `insider`; the Macro agent may depend on `institutional`.

**Research (2026-08-24):** `edgartools` (github.com/dgunning/edgartools) is a mature, free, no-API-key Python library that reads SEC EDGAR filings as structured data — 10-K, 10-Q, 8-K, Form 3/4/5 (insider), 13F (institutional), XBRL financials. Actively maintained (MCP server shipped March 2026). Returns Python objects / JSON, not HTML.

**Fix:** Refactor `insider` and `institutional` to use `edgartools` as the backend instead of raw HTML scraping. The `ToolResult` shape stays identical (so no downstream agent changes); only the implementation swaps. This is the single highest-leverage connector change for app stability.

**Files:** `docs/runtime/tools/insider.py`, `docs/runtime/tools/institutional.py` (rewrite internals, ~same line count). Add `edgartools>=2.0` to `docs/runtime/requirements.txt` and `pyproject.toml` deps.

### 3.3 The deferred-leads gap — the app's canvas opens gates that `DEFERRED.md` set

`docs/DEFERRED.md` gates the re-hire of several leads on "Re-hire if a flow needs X." The app's custom canvas lets a user *add* an agent to any graph — trivially satisfying "a flow needs X." Three leads are worth re-evaluating:

#### 3.3.1 Sentiment agent (deferred `sentiment-lead`)

**Gate in `DEFERRED.md`:** "Re-hire if the news tool layer matures past keyword mentions and needs NL tone-judgment."

**Today:** `sentiment_social` (Stocktwits) exists in Tier 3 but is marked "Paid/specialty." Research: Stocktwits API is **free, no auth, 30 messages/request** (api-docs.stocktwits.com). It's not actually paid — the catalog mislabels it. The gate is half-open: we have the data source, we don't have the agent.

**Recommendation:** Ship a **Sentiment** agent-library node in Phase 3.5 (a mini-phase after Phase 3) that consumes `sentiment_social` (relabeled Tier 1 free) + `news` (Google RSS) and produces a `sentiment` section with NL tone-judgment, retail-message-volume trend, and a self-skeptical confidence label. **Honest about its own noise** per `docs/USER-JOBS.md` no-build list ("Sentiment is mostly noise… the system is skeptical of itself by design").

**Catalog fix:** Move `sentiment_social` from Tier 3 to Tier 1 (free, no key). Update `docs/V1-CONNECTORS.md` §2.3 → §2.1.

#### 3.3.2 Options-flow agent (deferred `options-flow-insider` specialist)

**Gate in `DEFERRED.md`:** "Re-hire if a user pays for an options-flow data source."

**Today:** `options_chain` (Finnhub, Tier 3) exists. `short_interest` (Finnhub, Tier 3) exists. The data is reachable with a free Finnhub key (60 req/min). The gate ("user pays") is wrong — Finnhub's free tier covers options chain + short interest.

**Recommendation:** Do **not** ship an Options-flow agent in app v1. The data exists but the *signal* is contested (per `docs/CANNOT-DO.md` "Will always be lossy" §2 — free models are 50–70% as good on adversarial reasoning, and options-flow interpretation is adversarial). Defer to a future agent-library entry once the Quant + Macro agents prove the pattern. **Document the deferral** in `app/docs/AGENT-LIBRARY.md` §4 (future entries).

#### 3.3.3 Altdata agent (deferred `altdata-lead`)

**Gate in `DEFERRED.md`:** "Re-hire if a paid data source or scrape pipeline goes live."

**Today:** No altdata connectors exist. Satellite/supply-chain/credit-card/web-traffic data is all paid (Pitchbook, CB Insights, etc.). The gate is not met.

**Recommendation:** Do **not** ship an Altdata agent. The gate is genuinely unmet — no free altdata source exists in 2026. Leave deferred. Document in `app/docs/AGENT-LIBRARY.md` §4.

### 3.4 The fundamentals redundancy — FMP vs yfinance

**Observation:** The project has `fundamentals` (FMP, Tier 2, 250 req/day) for income/balance/cashflow, but `yfinance` (already a dep) also returns financial statements for free, no key, no rate limit. The MonetaiQ 2026 review notes yfinance's financials are "shallow" and "community-maintained scrapers that break regularly."

**Recommendation:** Add a **free fundamentals connector** `fundamentals_yf` backed by `yfinance`'s `income_stmt` / `balance_sheet` / `cashflow` methods. Use it as the default; fall back to `fundamentals` (FMP) when the user has a key and yfinance fails. This gives the Macro + Quant agents a keyless path. **Not blocking for app v1** — the Quant agent already works with the deterministic `quant_*` tools; this is a Phase 5+ enhancement.

---

## 4. The recommended connector additions / changes

Ordered by leverage (highest first):

| # | Change | Type | Tier | Phase | Effort |
|---|---|---|---|---|---|
| 1 | **`quant_indicators`** — new deterministic connector wrapping `pandas-ta` (RSI, MACD, MA, VWAP, Bollinger) | New | 4 (quant) | Phase 3 (needed by Technical agent) | Small (~150 lines) |
| 2 | **Refactor `insider` to use `edgartools`** — swap OpenInsider scrape for SEC-direct structured data | Refactor | 1 | Phase 3 (needed by Flow-and-transcript) | Small (internals swap) |
| 3 | **Refactor `institutional` to use `edgartools`** — swap 13F HTML parse for SEC-direct | Refactor | 1 | Phase 3 (macro context) | Small (internals swap) |
| 4 | **Relabel `sentiment_social` Tier 3 → Tier 1** — Stocktwits API is free, no auth | Catalog fix | 1 | Phase 3.5 (with Sentiment agent) | Trivial |
| 5 | **`fundamentals_yf`** — free fundamentals via yfinance (keyless fallback to FMP) | New | 1 | Phase 5+ (enhancement) | Small (~100 lines) |

**Not recommended (gates unmet or contested):**
- Options-flow agent — data exists but signal is contested; defer.
- Altdata agent — no free data source; leave deferred.
- TAAPI.IO — paid, network-dependent, adds a key; local compute via `pandas-ta` is strictly better.

---

## 5. How this maps to `app/docs/AGENT-LIBRARY.md`

The agent-library JSON for the Technical and Flow-and-transcript nodes needs updating once the connectors ship:

### Technical agent (after `quant_indicators` ships)

```json
{
  "id": "technical",
  "connectors_consumed": ["market_data", "quant_indicators"],
  ...
}
```

### Flow-and-transcript agent (after `insider` refactor)

No JSON change — `connectors_consumed: ["insider", "transcripts"]` stays the same; the connector's backend swap is transparent.

### Macro agent (after `institutional` refactor + `macro` connector listed)

```json
{
  "id": "macro",
  "connectors_consumed": ["market_data", "macro", "institutional"],
  ...
}
```
(`AGENT-LIBRARY.md` currently lists only `market_data` for Macro — this was an oversight; `macro` (FRED) and `institutional` should be listed.)

### Sentiment agent (new, Phase 3.5)

```json
{
  "id": "sentiment",
  "display_name": "Sentiment (self-skeptical)",
  "connectors_consumed": ["sentiment_social", "news"],
  "default_model": "ollama/llama3.3:70b",
  "system_prompt_ref": "docs/prompts/library/sentiment/system-prompt.md",
  ...
}
```

---

## 6. What this doc doesn't do

- It does **not** add connectors to `docs/runtime/call_tool.py`'s `TOOL_REGISTRY` — that's implementation work for Phase 3.
- It does **not** update `docs/V1-CONNECTORS.md` — that happens when each connector ships, per the "Adding a New Connector" recipe in that file.
- It does **not** change the app's `PROTOCOL.md` — the WS bridge is connector-agnostic; new connectors surface via the same `connector_requested` / `connector_completed` events.

The implementing agent should pick up item #1 (`quant_indicators`) first in Phase 3, since the Technical agent is blocked without it.
