# Sentiment (Room 7)

> Ground Floor — Intake
> Lead: **Cathie Wood**

Sentiment reads the mood. Options flow, social media, insider moves, analyst revisions — tracking what the market is feeling and what the smart money is actually doing.

## Agents

| Agent | File |
|-------|------|
| **Cathie Wood** — Lead Sentiment | [`cathie-wood/`](cathie-wood/) |
| News Sentiment Agent | [`news-sentiment/`](news-sentiment/) |
| Social Media & Retail Agent | [`social-media-retail/`](social-media-retail/) |
| Insider & Institutional Agent | [`insider-institutional/`](insider-institutional/) |
| **Jon Najarian** — Options Flow & Dark Pool Agent | [`options-flow-dark-pool/`](options-flow-dark-pool/) |
| Analyst & Earnings Revision Agent | [`analyst-earnings-revision/`](analyst-earnings-revision/) |

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `TWITTER_API_KEY` | Twitter/X API v2 | Social media sentiment, trending tickers, retail chatter |
| `NEWSAPI_KEY` | NewsAPI | News articles for sentiment analysis and narrative tracking |
| `POLYGON_API_KEY` | Polygon.io | Options flow, dark pool prints, and institutional order data |
| `FINANCIAL_DATASETS_API_KEY` | Financial Datasets | Analyst estimates, EPS revisions, and price targets |
| — | SEC EDGAR (free) | 13F filings and insider Form 4 transactions. No API key required. |

Set in `.env` or environment: `export VARIABLE="your-key-here"`
