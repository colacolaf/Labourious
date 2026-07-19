# Labourious Security

## Philosophy

Local-first. Your machine, your keys, your data. Nothing leaves without your explicit configuration.

---

## What's Encrypted

| Data | Encryption | Location |
|------|-----------|----------|
| Broker API keys | AES-256, PBKDF2 | Encrypted vault on disk |
| API secrets | AES-256, PBKDF2 | Encrypted vault on disk |
| LLM API keys | AES-256, PBKDF2 | Encrypted vault on disk |

## What's Local (Not Encrypted, Not Transmitted)

| Data | Notes |
|------|-------|
| Trade history | SQLite DB |
| Agent configurations | Local files |
| Conversation history | Local vector DB |
| Knowledge graph | Local storage |
| User rules/mandates | PM system prompt |

---

## LLM Data Flow

- **Ollama (local):** All data stays on your machine. Zero external transmission.
- **Claude/GPT/Gemini (cloud):** Your prompts and market data are sent to the provider's servers over HTTPS. Review their privacy policies. Labourious never sees this data — it routes directly.

---

## Key Management

- **Vault password:** Set on first run. Required to decrypt broker/API keys.
- **Not stored anywhere.** Cannot be recovered if forgotten.
- **Encrypted backup:** Optional. Store somewhere safe (external drive, not cloud).

**Best practices:**
- Use strong vault password (12+ chars, mix case, numbers, symbols)
- Create broker API keys with limited permissions
- Rotate keys every 6 months
- Never share vault password

---

## If Credentials Are Compromised

1. Stop all agents immediately
2. Revoke compromised API keys on broker/provider websites
3. Generate new keys
4. Update vault
5. Check accounts for unauthorized activity

---

## Open Source

All encryption code is in the repository — auditable by anyone. Trust through transparency, not obscurity.

---

*Security documentation will be expanded as implementation progresses.*
