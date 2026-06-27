# SECRET SCRUBBING — API KEY & CREDENTIAL PROTECTION

## Core Rule
No secret ever appears in: code, logs, error messages, test output, git commits,
print statements, f-strings in exceptions, or any output that leaves the vault.

## What Counts as a Secret
- API keys (any provider: Kraken, IBKR, Anthropic, OpenAI, etc.)
- Private keys, signing secrets
- Passwords, passphrases
- Database connection strings with credentials
- JWT secrets, session tokens
- Webhook signing secrets
- SMTP passwords

## Source of Truth
This repo: `EncryptedVault` (`backend/vault/encrypted_vault.py`)
ALL secrets → vault. Never:
- `.env` committed to git
- Hardcoded in any `.py` or `.js` file
- In SQLite DB columns
- In log output

## Code Generation Rules
When generating code that uses credentials:
```python
# CORRECT
api_key = vault.get('kraken_api_key')

# WRONG — never generate this
api_key = "sk-abc123..."
api_key = os.environ.get('KRAKEN_KEY')  # acceptable only in vault loader itself
```

## Logging Guard
```python
# CORRECT
logger.error("API call failed", extra={"status": response.status_code})

# WRONG — never generate this
logger.error(f"API call failed with key {api_key}")
```

## Pre-Commit Check (mental)
Before suggesting a commit, scan diff for:
- Strings matching `[A-Za-z0-9]{20,}` in non-test files (potential key)
- Any file named `.env`, `secrets.json`, `credentials.json`
- Any `password=`, `secret=`, `apikey=` assignments with literal values

If found → block commit, flag to user.

## Test Fixtures
Use `faker` for fake credentials in tests. Never use real keys, even in comments.
```python
fake_api_key = fake.sha256()  # not a real key
```

## 14-Type PII Detection (applied to all generated output)
Never include in output: SSN, credit card numbers, phone numbers, email addresses
of real users, physical addresses, government IDs, health data.
