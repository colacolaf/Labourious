# Labourious Security Model

Local-first: your keys, your data, your machine.

## Principles

1. **No cloud dependency.** The app runs entirely on the user's machine. LLM calls go directly from the app to the provider the user configured (or to local Ollama).
2. **User-owned secrets.** API keys are entered by the user and stored in the OS keychain via Electron `safeStorage` where available, with a plain local file fallback. Keys are never logged, never sent anywhere except the provider they belong to, and never embedded in prompts sent to other providers.
3. **Local data.** Chat history, agent notes, config, and custom agents live in the user's data directory. Nothing is telemetried.

## Threat Notes

| Concern | Mitigation |
|---------|------------|
| Key exfiltration | Keys stay in keychain/config; the app never transmits them to any endpoint except the configured provider |
| Prompt injection from web content | Agents are prompted with source-verification and connector-failure protocols; fetched content is treated as untrusted data |
| Connector abuse | Connector calls are logged locally; rate limits and provider keys are user-owned |
| Malicious custom agents | User-added agents run under the same runtime as base agents — prompts are just text; connectors are the only capability surface |
| Broker/trade actions | Execution category is out of skeleton scope; when added, it will require explicit user confirmation per order |

## Encryption

- Secrets: OS keychain / `safeStorage` (AES-256 under the hood on supported platforms)
- At-rest chat history and notes: plain files on the user's own disk (encrypted at rest is a post-skeleton option)

## Offline Mode

Core functionality works offline with a local Ollama model. Connectors that need the internet degrade gracefully (agents report `CONNECTOR STATUS: FAILED` and fall back to what they have).
