# Phase 3B Design Spec — Advanced LLM Integration

**Date:** 2026-06-20
**Status:** Approved for implementation
**Phase:** 3B of 3

---

## 1. Scope

Phase 3B adds GPT-4o as a third LLM provider, global LLM switching via a config file, cost estimation per provider, and a 6th LLM tab in AgentInspector for the UI.

**In scope:**
- `openai_client.py` — async OpenAI wrapper (same interface as `claude_client.py`)
- `cost_estimator.py` — $/month formula for Ollama / Claude / GPT-4o
- `data/llm_config.json` — persistent global LLM config (provider + model)
- `backend/llm/config.py` — read/write helpers for the config file
- `backend/api/llm_config.py` — REST: GET/PATCH config, POST test
- LLM router extended with OpenAI branch
- `LLMTab.jsx` — 6th tab in AgentInspector
- OpenAI API key stored/retrieved via existing vault (key: `openai_api_key`)

**Out of scope:** per-agent LLM switching (deferred), streaming responses, fine-tuning.

---

## 2. Architecture

### New backend files

```
backend/llm/
├── openai_client.py       # AsyncOpenAI wrapper
├── cost_estimator.py      # $/month estimate per provider
└── config.py              # LLMConfig dataclass + read_config/write_config helpers

backend/api/
└── llm_config.py          # GET/PATCH /api/llm/config, POST /api/llm/test
```

### Modified backend files

| File | Change |
|---|---|
| `backend/llm/llm_router.py` | Add OpenAI branch; read provider from `LLMConfig` singleton |
| `backend/main.py` | Import + register `llm_config_router` |

### New frontend files

```
frontend/src/components/Warroom/LLMTab.jsx
```

### Modified frontend files

| File | Change |
|---|---|
| `frontend/src/components/Warroom/AgentInspector.jsx` | Add `'LLM'` to `TABS`; render `<LLMTab>` |
| `frontend/src/utils/api-client.js` | Add `llmApi` named export |

---

## 3. Config File

**Path:** `data/llm_config.json` (gitignored)

```json
{
  "provider": "ollama",
  "model": "mistral",
  "ollama_url": "http://localhost:11434"
}
```

Valid providers: `"ollama"`, `"claude"`, `"openai"`.

Defaults to `{provider: "ollama", model: "mistral"}` if file missing or corrupt. Never stores API keys — those live in vault only.

---

## 4. Backend: `backend/llm/config.py`

```python
from dataclasses import dataclass, asdict
import json, os

CONFIG_PATH = "data/llm_config.json"

DEFAULTS = {"provider": "ollama", "model": "mistral", "ollama_url": "http://localhost:11434"}

@dataclass
class LLMConfig:
    provider: str = "ollama"
    model: str = "mistral"
    ollama_url: str = "http://localhost:11434"

def read_config() -> LLMConfig:
    try:
        with open(CONFIG_PATH) as f:
            data = {**DEFAULTS, **json.load(f)}
        return LLMConfig(**{k: data[k] for k in LLMConfig.__dataclass_fields__})
    except Exception:
        return LLMConfig()

def write_config(cfg: LLMConfig) -> None:
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(asdict(cfg), f, indent=2)
```

---

## 5. Backend: `backend/llm/openai_client.py`

Same interface as `claude_client.py`: single `async def generate(prompt: str) -> Optional[str]`.

```python
from openai import AsyncOpenAI
from typing import Optional

class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, prompt: str) -> Optional[str]:
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            timeout=30.0,
        )
        return resp.choices[0].message.content
```

---

## 6. Backend: `backend/analytics/cost_estimator.py`

```python
# Token/cost constants (update per model release)
PRICES = {
    "ollama": 0.0,
    "claude": {"claude-sonnet-4-6": 3.0 / 1_000_000},    # $3/M input tokens
    "openai": {"gpt-4o": 5.0 / 1_000_000},                # $5/M input tokens
}
TOKENS_PER_CALL = 800  # prompt ~600 + response ~200

def estimate_monthly_cost(provider: str, model: str, check_frequency_seconds: int) -> float:
    """Returns estimated $/month. check_frequency_seconds=0 → 0.0."""
    if provider == "ollama" or check_frequency_seconds <= 0:
        return 0.0
    calls_per_month = (86400 / check_frequency_seconds) * 30
    price = PRICES.get(provider, {})
    if isinstance(price, dict):
        price = price.get(model, 0.0)
    return round(TOKENS_PER_CALL * calls_per_month * price, 2)
```

---

## 7. Backend: `backend/api/llm_config.py`

```
GET  /api/llm/config  → {provider, model, ollama_url, has_openai_key, has_claude_key}
PATCH /api/llm/config → {provider?, model?, ollama_url?} → 200 or 422
POST /api/llm/test    → {} → {ok: bool, latency_ms: int, error?: str}
```

- `has_openai_key` / `has_claude_key` — boolean derived from vault lookup (never returns key material)
- PATCH validates `provider` ∈ `{ollama, claude, openai}`; returns 422 if `provider=openai` and vault has no `openai_api_key`
- POST test calls `router.decide()` with dummy market data, measures latency

---

## 8. LLM Router Extension

`LLMRouter.__init__` gains `openai_client: Optional[OpenAIClient] = None` and `provider: str`.

`decide()` routing:
```python
if self.provider == "openai" and self._openai:
    raw = await self._openai.generate(prompt)
elif self.provider == "claude" and self._claude:
    raw = await self._claude.generate(prompt)
else:
    raw = await self._ollama.generate(prompt)   # default fallback
```

Router is re-initialised on every PATCH `/api/llm/config` call (config change takes effect immediately, no restart).

---

## 9. Frontend: LLM Tab

```
┌─ [Overview][Trades][Rules][Performance][Settings][LLM] ─┐
│                                                           │
│ LLM MODEL                                                 │
│                                                           │
│ ● Ollama (Local)                                          │
│   Model: [mistral ▼]    Status: ✅ Running                │
│   Cost: Free                                              │
│                                                           │
│ ○ Claude                                                  │
│   API Key: [connected via vault ✅]                       │
│   Est. cost: ~$2.40/month                                 │
│                                                           │
│ ○ GPT-4o                                                  │
│   API Key: [●●●●●●●●●●  ✏ edit]  ← saves to vault        │
│   Est. cost: ~$8.10/month                                 │
│                                                           │
│ [TEST LLM]   [SAVE]                                       │
└───────────────────────────────────────────────────────────┘
```

- Cost estimates computed frontend-side using `check_frequency` from the selected agent + constants matching `cost_estimator.py`
- "Test LLM" → `POST /api/llm/test` → shows inline `✅ OK (210ms)` or `❌ error message`
- API key input for GPT-4o: masked, saves via `PUT /api/vault/openai_api_key` on blur (existing vault endpoint)
- "SAVE" → `PATCH /api/llm/config` with selected provider + model

### `llmApi` (api-client.js additions)

```js
export const llmApi = {
  getConfig: () => apiClient.get('/api/llm/config'),
  patchConfig: (data) => apiClient.patch('/api/llm/config', data),
  test: () => apiClient.post('/api/llm/test'),
};
```

---

## 10. Security

- OpenAI API key stored in vault (`openai_api_key`), same pattern as `anthropic_api_key`
- `GET /api/llm/config` returns `has_openai_key: bool` only — never returns key material
- Config file (`data/llm_config.json`) contains no secrets — safe to read/write without encryption
- All LLM calls respect existing 30s timeout from httpx defaults
- `cost_estimator.py` reads `check_frequency` from DB, never token counts from LLM responses

---

## 11. Testing

| File | What it tests |
|---|---|
| `tests/test_openai_client.py` | Mock `AsyncOpenAI` — generate OK, timeout, malformed response |
| `tests/test_cost_estimator.py` | All providers, edge cases (zero frequency, unknown model) |
| `tests/test_llm_config_api.py` | GET config, PATCH valid/invalid provider, POST test |

No new frontend tests — LLMTab is UI wiring only.

---

## 12. File Checklist

### New files
- `backend/llm/openai_client.py`
- `backend/llm/config.py`
- `backend/analytics/cost_estimator.py`
- `backend/api/llm_config.py`
- `frontend/src/components/Warroom/LLMTab.jsx`
- `tests/test_openai_client.py`
- `tests/test_cost_estimator.py`
- `tests/test_llm_config_api.py`

### Modified files
- `backend/llm/llm_router.py`
- `backend/main.py`
- `frontend/src/components/Warroom/AgentInspector.jsx`
- `frontend/src/utils/api-client.js`

### Data
- `data/llm_config.json` — created at first PATCH or on startup defaults
- `.gitignore` — add `data/llm_config.json` if not already ignored

---

## 13. Success Criteria

- LLM provider switch takes effect on next agent decision cycle, no restart required
- Cost estimate in LLM tab within 15% of actual monthly cost at steady-state `check_frequency`
- Test endpoint returns latency ≤ 5s for all three providers (or clear error if key missing)
- Zero API keys in logs or error responses
- `pytest tests/test_openai_client.py tests/test_cost_estimator.py tests/test_llm_config_api.py -v` all pass
