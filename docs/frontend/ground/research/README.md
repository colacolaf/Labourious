# Research (Room 1)

> Ground Floor — Intake
> Lead: **Michael Burry**

Research digs for facts. The room that finds what others miss — in filings, on the web, in academic papers, and in the raw data.

## Agents

| Agent | File |
|-------|------|
| **Michael Burry** — Lead Researcher | [`michael-burry/`](michael-burry/) |
| Web Research Agent | [`web-research/`](web-research/) |
| **John Hempton** — SEC/Regulatory Agent | [`sec-regulatory/`](sec-regulatory/) |
| Hedge Fund & Political Filings Intern | [`hedge-fund-political-filings-intern/`](hedge-fund-political-filings-intern/) |
| Academic Research Agent | [`academic-research/`](academic-research/) |
| News Aggregation Agent | [`news-aggregation/`](news-aggregation/) |
| Data Scout Agent | [`data-scout/`](data-scout/) |

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `TAVILY_API_KEY` | Tavily | Web search for current information and primary sources |
| `NEWSAPI_KEY` | NewsAPI | News article aggregation across sources and date ranges |
| `FINANCIAL_DATASETS_API_KEY` | Financial Datasets | Structured financial data extraction |
| — | SEC EDGAR (free) | SEC filings — 10-K, 10-Q, 8-K. No API key required. |

Set in `.env` or environment: `export VARIABLE="your-key-here"`
