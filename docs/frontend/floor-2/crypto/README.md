# Crypto (Room 14)

> Floor 2 — Analysis
> Lead: **Vitalik Buterin**

Crypto covers the digital frontier. On-chain analytics, DeFi yields, tokenomics design, and protocol risk — understanding the assets and protocols that traditional finance doesn't yet have a framework for.

## Agents

| Agent | File |
|-------|------|
| **Vitalik Buterin** — Lead Crypto | [`vitalik-buterin/`](vitalik-buterin/) |
| **Alex Svanevik** — On-Chain Analytics Agent | [`on-chain-analytics/`](on-chain-analytics/) |
| DeFi & Yield Agent | [`defi-yield/`](defi-yield/) |
| Tokenomics Agent | [`tokenomics/`](tokenomics/) |
| Protocol Risk Agent | [`protocol-risk/`](protocol-risk/) |

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `COINGECKO_API_KEY` | CoinGecko (free tier) | Crypto price data, market cap, and on-chain metrics — shared by all Crypto room agents |
| `ETHERSCAN_API_KEY` | Etherscan | Wallet labels, transaction history, and smart contract verification |

Set in `.env` or environment: `export COINGECKO_API_KEY="your-key-here"`
