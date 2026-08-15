# Labourious Setup (Planned)

> The app is not built yet. This documents the intended setup for the skeleton release.

## 1. Install

Download the app (Electron) for your platform and open it — it runs like any desktop app. No server, no cloud account.

## 2. Add your API keys

Labourious uses **your** keys. Supported providers:

| Provider | Kind | Example |
|----------|------|---------|
| OpenAI-compatible | Chat/completions API | OpenAI, OpenRouter, local servers, most cloud providers |
| Anthropic | Claude API | claude-*-* models |
| Ollama | Local | fully offline |

Keys are stored in the OS keychain (via Electron `safeStorage`) where available, with a plain local config file fallback. Keys never leave your machine and are never logged.

## 3. Config file

`~/.labourious/config.json` (or the app's data directory):

```json
{
  "providers": {
    "openai": { "baseUrl": "https://api.openai.com/v1" },
    "anthropic": {},
    "ollama": { "baseUrl": "http://localhost:11434" }
  },
  "connectors": {
    "web_search": { "provider": "serper" },
    "market_data": { "provider": "yfinance" },
    "news": { "provider": "newsapi" }
  },
  "defaultModel": "openai/gpt-4o"
}
```

Secrets (API keys) are referenced by name, not stored in the config file, when keychain support is active.

## 4. Connectors

Each connector is provider-configurable in the app's Settings:

- **Web search:** Serper, Tavily, or Brave (each needs its own API key)
- **Market data:** yfinance-style (no key), Polygon.io (key), Financial Modeling Prep (key)
- **SEC EDGAR:** free, no key
- **News:** NewsAPI (key) or provider feeds

## 5. Agents

The app ships with 16 base leads. Everything about an agent — system prompt, model, connectors — is editable in the app and saved to files, so a roster is portable and shareable.

## 6. Data locations

| What | Where |
|------|-------|
| Config | `~/.labourious/config.json` |
| Secrets | OS keychain (safeStorage) / fallback file |
| Chat history | `~/.labourious/history/` |
| Agent notes | `~/.labourious/notes/<agent-id>/` |
| Custom agents | `~/.labourious/agents/` |
