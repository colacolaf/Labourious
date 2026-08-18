# CONNECTORS — what data sources we actually need, and why

> Curated list of data sources (connectors) for the Analyst's Bench. Every pick is grounded in evidence: an industry paper, a top-tier vendor's reference architecture, or a documented hallucination pattern. Every "no" is also grounded — sources we ruled out, with the reason.

This document sits between [`USER-JOBS.md`](USER-JOBS.md) (what the project is for) and [`TODO.md`](TODO.md) (what we build next). Read USER-JOBS first, then this, then TODO. The runtime layer is `docs/runtime/tools/` — every connector here must end up as one dataclass there with a `ToolResult` envelope (`status`, `data`, `as_of`, `source`, `note`).

---

## Why this matters (the connection to hallucination)

The Kang/Liu paper **"Deficiency of Large Language Models in Finance" (arXiv 2311.15548, Nov 2023)** ran the most cited empirical test. Findings, quoted from the paper:

> *"Off-the-shelf LLMs experience serious hallucination behaviors in financial tasks."*

Their three test categories:

| Task | Llama2-7B-Chat | GPT-3.5 | GPT-4 | With RAG | With tool-use (function call) |
|---|---|---|---|---|---|
| Financial abbreviation recognition (192 acronyms) | poor | mediocre | near-perfect once grounded | near-perfect | n/a |
| Long-form explanation of obscure terms (157 terms, FactScore) | very low | low | moderate | high | n/a |
| Stock price query (560 queries, 70 tickers, 4 dates) | fabricated | fabricated | fabricated | n/a | **near-exact** |

The takeaway is unambiguous: **stock prices must come from a function call, not from the LLM's memory.** Every "the LLM just knew that" assumption is a future bug.

Anthropic's May 2026 finance-agents release extends this empirically — they ship **21 connectors** with their reference templates (FactSet, S&P Capital IQ, MSCI, PitchBook, Morningstar, Chronograph, LSEG, Daloopa, Dun & Bradstreet, **Financial Modeling Prep**, Guidepoint, IBISWorld, SS&C Intralinks, Third Bridge, Verisk, Moody's via MCP). The signal from naming these together: any non-trivially defensible memo needs **at least the 7 categories below**, and ideally several sources per category.

---

## What the consensus says about how many sources you need

Four independent bodies of evidence converge:

1. **Anthropic multi-agent research paper (2025)**: *"Token usage by itself explains 80% of the variance [in BrowseComp], with the number of tool calls and the model choice as the two other explanatory factors."* Tool count is the second most important lever. Quality, not just count.

2. **Toolformer (Meta AI, 2023)**: without strict filtering, **90–99% of LLM-generated API calls are useless** — but the 1–10% that fire correctly are transformative. Therefore: build the connector layer with discipline (filter, validate, cite), not as a firehose.

3. **Ant Group RLFKV (arXiv 2602.05723, 2026)**: decompose every claim into atomic knowledge units, then verify each unit against retrieved documents. **Implication: every connector output must be granular enough to attach to a specific clause of the memo, not a single JSON blob.**

4. **CFA Institute RAG case study (2024)**: hybrid is the right pattern — *"Structured financial data—such as earnings reports and balance sheets—are best handled through application programming interfaces (APIs) and traditional data pipelines, qualitative disclosures in corporate filings present a different challenge."* Two modes, not one.

Crystallized into a minimum-viable connector set:

> **A defensible memo on a US public company needs AT LEAST**: (1) primary filings index, (2) primary filings full-text search, (3) current price + history, (4) earnings call transcripts, (5) recent news + 8-K wire, (6) insider transactions, (7) institutional ownership. Anything less, the LLM will hallucinate at least one section.

---

## Current stack — what's already in `docs/runtime/tools/`

| Tool | Source behind it | Free? | Auth | Status |
|---|---|---|---|---|
| `sec_edgar.py` | `data.sec.gov` REST | ✅ keyless | User-Agent string | shipping |
| `news.py` | `news.google.com` RSS, fallback NewsAPI.org | ✅ RSS free / paid key | none / `NEWSAPI_KEY` env | shipping |
| `market_data.py` | `yfinance` (prices) + `api.stlouisfed.org` (macro) | ✅ yfinance free / FRED free w/ key | none / `FRED_API_KEY` env | shipping |
| `web_fetch.py` | generic HTTP + boilerplate strip | ✅ keyless | none | shipping |

**Shipped**: 4 connectors. **Largest gaps**, in priority order:

1. **Earnings call transcripts** — nothing currently exposes these. The senior-analyst's primary qualitative source for guidance / tone / "what management actually said" lives here. Without it, the memo has no management voice.
2. **SEC full-text search (EFTS)** — current `sec_edgar.py` only fetches the recent-filings index for one ticker. We can't ask "show me all NVDA 8-Ks that mention 'guidance'" or "find all proxies with golden-parachute disputes." Ant Group's RLFKV paper assumes exactly this capability.
3. **Insider transactions (Form 4)** — the sentiment lead's primary signal. Cluster buys + size of buy + frequency is the most cited behavioral signal in public-company equity research.
4. **13F institutional ownership** — strategy and sentiment leads. Smart-money inventory shift is the second-most-cited behavioral signal.
5. **Earnings calendar / upcoming events** — flow `f3-earnings-preview` and the orchestrator's freshness tier need this.
6. **Analyst consensus / ratings** — flow `f2-compare-tickers` and the bull/bear case balance benefit. Optional, but high-leverage.
7. **Options chain / short interest** — flow `f7-risk-event` and flow for volatility-shock memos want this. Defer until tier-1 ships.

---

## The curated list

### TIER 1 — Build first (free, no key, must ship)

These are the **non-negotiables**. Every memo must be able to touch each of these or it can't claim defensibility.

| Slug | Provider | Endpoints | Free? | Why this slot |
|---|---|---|---|---|
| `sec_edgar` | SEC EDGAR | `/files/company_tickers.json`, `/submissions/CIK*.json`, archive paths | ✅ keyless | Primary issuer filings (10-K, 10-Q, 8-K, DEF 14A) — same data the auditors see |
| `sec_edgar_fulltext` | **efts.sec.gov** | `/eftsx/query` full-text + form filter + date range | ✅ keyless | Ask "all NVDA 8-Ks since Jan 1 mentioning 'guidance'" in one call. Replaces the missing primary-discovery layer. |
| `quotes` | yfinance | ticker→OHLCV, options chain, short interest | ✅ keyless | Delayed price tape (15-min) — sufficient for analyst memos. Replaces `market_data.price_history`. |
| `macro` | FRED | `/fred/series/observations` | ✅ free w/ key (`FRED_API_KEY`) | Fed funds rate, 10y-2y spread, CPI, unemployment, Sahm rule — every macro overlay depends on this |
| `news_rss` | Google News RSS | topic→RSS feed | ✅ keyless | Cheap headline discovery; companion to 8-K wire for change-of-events |
| `news_8k` | SEC EDGAR + RSS | All 8-Ks since N days ago, filtered for tickers | ✅ keyless | 8-K is the legally-mandated material-event disclosure — this is the primary event wire |
| `insider` | **OpenInsider (openinsider.com)** | scrape Form 4 aggregation tables since Date for Ticker | ✅ keyless | Cluster buys, CEO-CFO direct buys, $20k+ purchases — the most-cited insider signal. OpenInsider is the consensus free reference for Form 4. |
| `institutional` | **SEC EDGAR 13F + WhaleWisdom** | `/submissions/CIK*.json` for 13F-HR filings; WhaleWisdom for normalized comparison | ✅ keyless | Quarterly smart-money positions — the second-most-cited smart-money signal |
| `transcripts` | SeekingAlpha | `/earnings/earnings-call-transcripts` public pages | ✅ free but scraping ToS-grey | Free, ~4,500 transcripts per quarter. Mirror via local cache on first fetch. Paid fallback: FMP/AC's transcript API |

**Why this tier first**: every connector here is free, every one is keyless or near-keyless, every one is the canonical free reference for its data type. Combined, they expose **8 of the 10 categories** that the literature says a defensible memo must draw on. The remaining 2 (options / analyst consensus) are tier-2 upgrades.

What the literature says specifically about each:

- **SEC EDGAR** in any form: not in question. Hallucination on primary filings was the #1 cause of production-quality failures in Kang/Liu.
- **EFTS full-text**: explicitly cited by the Ant Group RLFKV paper as necessary; SEC exposes it for free at `https://efts.sec.gov/LATEST/search-index?q=...&dateRange=custom&startdt=...&enddt=...&forms=8-K`.
- **yfinance** for delayed prices: the consensus choice in the broader Python ecosystem; Medium's 2025 financial-API comparison article ranks it "frequent IP bans make it unreliable for production" but it's fine for the analyst-memo cadence.
- **FRED**: 845,000 series, 126 sources, free key in 60 seconds. Universally used in academic and industry research; no serious competitor.
- **Google News RSS**: the Firecrawl review (May 2026) and every block-of-text-tier analyst-news tool defaults to it. Zero abuse pressure at sub-100 req/min.
- **OpenInsider**: cited in reddit r/Daytrading, stablebread.com, and tradealgo.com as *"the consensus free tool for tracking insider transactions … aggregates Form 4 filings into a sortable … real-time … SEC …"*. The site is a single-host scrape, no API needed; the SEC data underneath it is the same EDGAR pulls we already make.
- **WhaleWisdom + EDGAR 13F**: 13F-HR is a primary SEC filing, so EDGAR is the primary source. WhaleWisdom is the standard normalized front-end.

Tier 1 totals: **9 connectors, all free, all keyless or near-keyless.**

### TIER 2 — Build second (free with key, higher rate limits, paid upgrade paths)

| Slug | Provider | Endpoints | Free tier | When it earns its slot |
|---|---|---|---|---|
| `quotes_realtime` | **Finnhub** | `/api/v1/quote`, `/stock/profile`, `/news-sentiment` | ✅ 60 req/min | Real-time quotes (vs yfinance 15-min delay), analyst ratings & price targets out of the box, news sentiment score |
| `fundamentals` | **Financial Modeling Prep (FMP)** | `/api/v3/income-statement`, DCF, ratios, key-metrics | ✅ 250 req/day | Pre-built DCFs, ratios, 30+ years of statements — saves the analyst days of manual computation |
| `transcripts_paid` | **FMP transcripts** | `/api/v4/earning_transcript` | ⚠️ paid tier | When SeekingAlpha scraping breaks or quota is hit |
| `newsapi` | NewsAPI.org | `/v2/everything` | ✅ 100 req/day | Higher-quality news discovery (Reuters, WSJ where RSS misses) |
| `consensus` | Finnhub (upgrade) or FMP | `/stock/recommendation`, price target | ✅ part of free Finnhub | Sell-side consensus when comparing tickers (f2) |
| `calendars` | Finnhub or FMP | `/calendar/earnings`, `/calendar/ipo` | ✅ part of free | Orchestrator's freshness tier + f3 preview flow |

**Why this tier second**: each is gated by either a free API key (5-line signup) or a low-cost free tier. They are quality-of-life upgrades — not new categories of evidence. The senior analyst can write a memo on tier 1 alone; tier 2 makes the workflow cheaper and faster.

### TIER 3 — Defer (paid, US-only specialty, niche)

| Slug | Provider | Why deferred |
|---|---|---|
| `options_realtime` | **Massive.com (ex-Polygon)** | $29/mo+ for real-time options Greeks, OI flow. Important for flow `f7-risk-event` but flow doesn't yet ship. Free yfinance options chain is good enough until v1 ships. |
| `intraday` | Polygon.io / Massive | 5/min free tier is unusable; $79/mo gets tick. Analyst memos don't need ticks — daily bars suffice. |
| `intraweek_technical` | Alpha Vantage | 25 req/day free → equivalent to a few tickers. Useful but ad-hoc; hard to design a tool layer around. |
| `sentiment_quant` | Unusual Whales, Menthor Q | Paid and US-only. Useful for sentiment but not yet on the critical path. |
| `altdata_congress` | Quiver Quantitative | Free 5k credits/mo. Has niche value for `f4-earnings-review` (congress trades around earnings), but no published accuracy benchmark — defer until validated. |
| `fx_crypto` | FMP `forex`, `crypto` | Free with FMP key. Defer — the Wharton comp v1 is US equities only. |

### DEFERRED INDEFINITELY — kill list

| Slug | Reason |
|---|---|
| `factset`, `bloomberg`, `lseg_refinitiv`, `capital_iq`, `pitchbook`, `morningstar_direct`, `ibisworld` | Paid, enterprise-only, six-figure annual contracts. Out of free-model mission. |
| `alpha_sense`, `sentieo`, `daloopa` | Premium broker-research terminals. Out of free-model mission. |
| `moodys_premium` | Credit ratings behind enterprise gate. The free-tier ontology isn't granular enough for equity research. |
| `esg_sustainalytics`, `msci_esg`, `refinitiv_esg` | ESG data has accuracy problems even with full access; the v1 thesis doesn't ask for it. |
| `private_market_valuation` (PitchBook) | Public-equity focus is the v1 job. Private market data lives elsewhere. |
| `global_equities` (non-US/Canada) | Adds 4× complexity for tiny marginal research value. v2 problem. |

---

## How the analyst roles consume it

Mapping each lead role to the connectors it touches. This is the input to the runtime — every role gets a curated envelope for each flow:

| Role (`docs/prompts/leads/<role>/system-prompt.md`) | Connectors it must hit | Connectors it may hit |
|---|---|---|
| **fundamental** | `sec_edgar`, `sec_edgar_fulltext`, `quotes` | `fundamentals` (FMP), `transcripts`, `transcripts_paid` |
| **macro** | `macro` (FRED) | `news_rss`, `news_8k` |
| **strategy** | `sec_edgar_fulltext` (for comparable 10-Ks), `quotes` | `institutional` (13F), `consensus` |
| **sentiment** | `news_rss`, `news_8k`, `insider` (Form 4 cluster buys) | `newsapi`, `institutional` |
| **technical** | `quotes` (OHLCV, options chain) | `intraday` (defer) |
| **risk** | `quotes`, `sec_edgar_fulltext` (8-Ks) | `options_realtime` (defer), `intraday` (defer) |
| **research** | everything | everything — research is the meta-role that fans out |
| **critique** (devil's-advocate) | same as the role it's challenging | pulls prior theses from thesis_register, not connectors |

**Why this matters**: leads don't pick connectors freely. The orchestrator decides which connectors fire for each flow's wave. This is Toolformer's principle applied: **the right connector for the question, not the menu of all connectors**.

---

## The minimum-viable stack (lazy path)

If the project could only afford to ship **5 connectors** (call this set `MVP-5`), they would be:

1. **`sec_edgar`** (primary filings)
2. **`sec_edgar_fulltext` (EFTS)** (primary filings full-text)
3. **`quotes`** (yfinance — price tape)
4. **`news_rss` + `news_8k`** (material events)
5. **`insider`** (Form 4 cluster buys)

These 5 cover the structural backbone. FRED `macro`, `institutional` 13F, and `transcripts` are quality upgrades; `quotes_realtime` (Finnhub) and `fundamentals` (FMP) are conveniences; everything in tier 3 is a side quest.

**Minimum-viable memo**: a memo that cites only MVP-5 will be **structurally defensible** (every claim traceable to a primary source) but **qualitatively weaker** than one that adds transcripts and EFTS full-text — the devil's-advocate will have less to work with, and the orchestrator's freshness tier will miss some material events.

---

## Decision matrix

| Decision | Choice | Why |
|---|---|---|
| Stay free-first | ✅ yes | The Audience (USER-JOBS) is free users. Paid escape hatches are tier 2, not required. |
| One primary key per provider | ✅ env var, fallback keychain | We ship `runtime/keys_storage.py` already; no new auth surface area. |
| Cache every connector result | ✅ SQLite-backed, 24-hour TTL | Same cache layer ties together `sec_edgar_fulltext`, `insider`, `news_8k` |
| Each connector must return `ToolResult` | ✅ enforce | status (SUCCESS/EMPTY/FAILED), data, as_of, source, note. The 5-test eval suite depends on this shape. |
| Each connector must respect a rate budget | ✅ enforce | SEC: 10 req/sec; FRED: 120 req/min; OpenInsider: polite-scraping; Google RSS: lower rate is OK |
| Each connector must have a pilot test | ✅ on every PR | Mocked HTTP at the dataclass boundary; pilot count grows. |

---

## What this changes in `docs/runtime/tools/`

Adding these connectors is mostly new files, not rewrites. Each new tool is a single dataclass in `docs/runtime/tools/<name>.py`:

```
docs/runtime/tools/
├── sec_edgar.py            (existing — keep + extend)
├── sec_edgar_fulltext.py   (NEW — wraps efts.sec.gov)
├── news.py                 (existing — add news_8k builder)
├── market_data.py          (existing — rebrand as "quotes")
├── quotes_realtime.py      (NEW — Finnhub real-time prices if key set)
├── fundamentals.py         (NEW — FMP statements + DCF + ratios)
├── insider.py              (NEW — OpenInsider scraper + raw EDGAR Form 4 fallback)
├── institutional.py        (NEW — WhaleWisdom scraper + EDGAR 13F fallback)
├── transcripts.py          (NEW — SeekingAlpha public scrape w/ cache)
├── transcripts_paid.py     (NEW — FMP fallback when scraping breaks)
├── newsapi.py              (NEW — optional NewsAPI.org)
├── consensus.py            (NEW — Finnhub price targets / FMP grades)
├── calendars.py            (NEW — Finnhub earnings calendar / IPO calendar)
├── macro.py                (NEW from market_data.py fred_series, broader catalog)
└── web_fetch.py            (existing — keep)
```

That's **~10 new files** for tier 1 + tier 2, **all buildable on the existing `ToolResult` railing**.

---

## Citation discipline (the thing that breaks if we don't)

Ant Group's RLFKV paper shows the failure mode when connectors aren't disciplined:

> *"Although the retrieved document explicitly states that as of March 31, 2025, the company's earnings per share (EPS) was 70.86 yuan, the model's output incorrectly associates this value with May 15, 2025, demonstrating a clear temporal inconsistency."*

Three rules every connector must obey:

1. **Every datum carries `as_of`** — the timestamp on the wire. The LLM never invents a date.
2. **Every datum carries a `source` URL** — the URL the LLM can cite. The 5-test eval suite uses this for `test_source_verification`.
3. **Every failed fetch is `FAILED` not `None`** — the runtime surfaces the failure in the agent's "gaps" section. The 5-test eval suite uses this for `test_abstention`.

These rules are already in `docs/runtime/tools/__init__.py` (`ToolResult` dataclass). They are enforced by `docs/runtime/evals/test_source_verification.py` and `test_abstention.py`.

---

## Next concrete moves (the feed into TODO.md)

The connector build order — every item is one new file + one pilot + one commit on existing pattern:

| ID | Connector | Tier | Effort | Unblocks |
|---|---|---|---|---|
| `conn-1` | `sec_edgar_fulltext.py` — EFTS query | T1 | small | f1, f4, f5: cross-filing pattern search |
| `conn-2` | `insider.py` — OpenInsider scrape + EDGAR fallback | T1 | small | sentiment role, f4 |
| `conn-3` | `institutional.py` — WhaleWisdom + EDGAR 13F | T1 | small | strategy + sentiment, f5 |
| `conn-4` | `transcripts.py` — SeekingAlpha scrape + cache | T1 | medium | fundamental role with management voice |
| `conn-5` | `news_8k.py` — 8-K wire from EDGAR | T1 | small | freshness tier, f4 event detection |
| `conn-6` | `quotes_realtime.py` — Finnhub wrapper | T2 | small | real-time price tape upgrade |
| `conn-7` | `fundamentals.py` — FMP wrapper | T2 | small | DCF + analyst-grade statements |
| `conn-8` | `consensus.py` — analyst ratings + PT | T2 | small | f2 compare |
| `conn-9` | `calendars.py` — earnings + IPO calendar | T2 | small | f3 preview, freshness tier |
| `conn-10` | `options_realtime.py` — Polygon/Massive | T3 | medium | f7 risk event |
| `conn-11` | `intraday.py` — Alpaca / Polygon | T3 | medium | hot-path technical signals |
| `conn-12` | `sentiment_quant.py` — Unusual Whales | T3 | medium | sentiment quantification |

Each gets a pilot (httpx.MockTransport, cache assertion, rate-limit assertion) following the existing pattern. Each lands in `<15 minutes` once the dataclass pattern is clear.

---

## References

- Kang, H. & Liu, X.-Y. (2023). *"Deficiency of Large Language Models in Finance: An Empirical Examination of Hallucination."* arXiv:2311.15548.
- Anthropic. *"How we built our multi-agent research system."* 2025.
- Anthropic. *"Agents for financial services."* May 2026.
- Schick, T. et al. (2023). *"Toolformer: Language Models Can Teach Themselves to Use Tools."* arXiv:2302.04761.
- Yan et al. (2024). *"Corrective Retrieval Augmented Generation (CRAG)."* arXiv:2401.15884.
- Yin, T. et al. (2026). *"Mitigating Hallucination in Financial Retrieval-Augmented Generation via Fine-Grained Knowledge Verification (RLFKV)."* arXiv:2602.05723.
- Pisaneschi, B. (2024). *"RAG for Finance: Automating Document Analysis with LLMs."* CFA Institute Research and Policy Center.
- Zhang, L. et al. (2024). *"FinBen: A Holistic Financial Benchmark for Large Language Models."* arXiv:2402.12659.
- Xie, Q. et al. (2023). *"PIXIU: A Comprehensive Benchmark, Instruction Dataset and Large Language Model for Finance."* NeurIPS 2023.
- Wu, S. et al. (2023). *"BloombergGPT: A Large Language Model for Finance."* arXiv:2303.17564.
- Yang, H. et al. (2023). *"FinGPT: Open-Source Financial Large Language Models."* arXiv:2306.06031.
- *"Beyond yFinance: Comparing the Best Financial Data APIs"* (Medium, 2025).
- *"7 Best Investment Research APIs for AI-First Use Cases."* Firecrawl Blog, May 2026.
