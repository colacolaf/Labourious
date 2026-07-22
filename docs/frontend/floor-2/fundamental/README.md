# Fundamental (Room 5)

> Floor 2 — Analysis
> Lead: **Warren Buffett**

Fundamental reads the companies. Valuation, moats, management, forensic accounting, catalysts, industry structure — understanding what a business is worth and whether it will stay that way.

## Agents

| Agent | File |
|-------|------|
| **Warren Buffett** — Lead Fundamental | [`warren-buffett/`](warren-buffett/) |
| DCF & Valuation Agent | [`dcf-valuation/`](dcf-valuation/) |
| Moat & Competitive Analysis Agent | [`moat-competitive-analysis/`](moat-competitive-analysis/) |
| Management Quality Agent | [`management-quality/`](management-quality/) |
| **Harry Markopolos** — Forensic Accounting Agent | [`forensic-accounting/`](forensic-accounting/) |
| Catalyst & Event Agent | [`catalyst-event/`](catalyst-event/) |
| Industry Structure Agent | [`industry-structure/`](industry-structure/) |

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `FINANCIAL_DATASETS_API_KEY` | Financial Datasets | Income statements, balance sheets, cash flow data for DCF and valuation |
| — | SEC EDGAR (free) | 10-K, 10-Q for forensic accounting. No API key required. |

Set in `.env` or environment: `export VARIABLE="your-key-here"`
