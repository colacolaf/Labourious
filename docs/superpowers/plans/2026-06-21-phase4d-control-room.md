# Phase 4D — Control Room Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `ControlRoom.jsx` placeholder with a fully-functional 6-section tabbed Control Room UI that reads from and writes to existing backend APIs.

**Architecture:** Single `ControlRoom.jsx` page with tab state, one `controlRoom.store.js` Zustand store holding all section data, and 6 focused section components under `frontend/src/components/ControlRoom/`. No new backend endpoints — all APIs already exist.

**Tech Stack:** React 18, Zustand (devtools), Framer Motion, existing `api-client.js` exports (`vaultApi`, `llmApi`, `agentsApi`, `healthApi`), CSS custom properties from `index.css`, `Button`/`Spinner` from `Common/`.

## Global Constraints

- All colors via CSS vars — never hardcode hex. Reference: `docs/phase4-design-reference.md` CSS Variables table.
- All animations via Framer Motion. Tab switch: `opacity` only, 0.2s easeOut.
- Zustand stores always wrapped in `devtools()`. Store name: `'control-room-store'`.
- Loading state: `<Spinner />` from `frontend/src/components/Common/Spinner.jsx`.
- Error state: red-bordered card + message in `var(--color-accent-danger)`.
- Empty state: muted text `color: var(--color-text-muted)`.
- `fontFamily: 'var(--font-mono)'` on all Control Room UI elements.
- No new npm packages — use only already-installed deps.
- No backend changes — consume existing endpoints only.
- Frontend tests via `react-scripts test` (Jest + React Testing Library). Run: `cd frontend && npm test -- --watchAll=false`.
- `agentsApi` shape: `list()` → `Array<{id, name, status, room, total_pnl, confidence_score, max_drawdown}>`. `start(id)`, `stop(id)`, `pause(id)` → updated agent object.
- `vaultApi` shape: `listKeys()` → `Array<string>`, `setKey({key, value})`, `deleteKey(key)`, `testConnection(exchange)`.
- `llmApi` shape: `getConfig()` → `{provider, model, ollama_url, has_openai_key, has_claude_key}`, `patchConfig(data)`, `test()` → `{ok, latency_ms, error?}`, `saveKey(keyName, value)`, `getCost(provider, model, checkFrequency)` → `{cost}`.
- Brokers API (no export in api-client yet — add in Task 1): `GET /api/brokers` → `Array<{broker_name, is_active, connected_at, last_tested_at}>`, `GET /api/brokers/available` → `{brokers: string[]}`, `POST /api/brokers/connect` body `{broker_name, api_key, secret, is_paper}`, `GET /api/brokers/{name}/test` → `{broker, connected, message}`.
- Settings API (no export in api-client yet — add in Task 1): `GET /api/settings` → `{llm, allocation: {max_portfolio_drawdown, default_position_size, max_agents}, app}`, `POST /api/settings/allocation` body `{max_portfolio_drawdown, default_position_size, max_agents}`, `POST /api/settings/vault-password` body `{current_password, new_password}`.

---

## File Map

**Create:**
- `frontend/src/stores/controlRoom.store.js` — all Control Room state + actions
- `frontend/src/components/ControlRoom/BrokerSection.jsx` — broker connections tab
- `frontend/src/components/ControlRoom/LLMSection.jsx` — LLM config tab
- `frontend/src/components/ControlRoom/AllocationSection.jsx` — capital allocation tab
- `frontend/src/components/ControlRoom/AgentManagementSection.jsx` — agent management tab
- `frontend/src/components/ControlRoom/RiskSection.jsx` — risk settings tab
- `frontend/src/components/ControlRoom/VaultSection.jsx` — vault & security tab
- `frontend/src/components/ControlRoom/index.js` — barrel export

**Modify:**
- `frontend/src/utils/api-client.js` — add `brokersApi` and `settingsApi` exports
- `frontend/src/pages/ControlRoom.jsx` — replace placeholder with tabbed layout

**Test:**
- `frontend/src/stores/__tests__/controlRoom.store.test.js` — store action tests

---

## Task 1: Add `brokersApi` and `settingsApi` to api-client.js

**Files:**
- Modify: `frontend/src/utils/api-client.js`

**Interfaces:**
- Produces: `brokersApi.list()`, `brokersApi.available()`, `brokersApi.connect(data)`, `brokersApi.test(name)`, `settingsApi.get()`, `settingsApi.patchAllocation(data)`, `settingsApi.changePassword(data)`

- [ ] **Step 1: Add exports to api-client.js**

Open `frontend/src/utils/api-client.js`. Add after the `notificationsApi` export block and before `export default apiClient`:

```js
export const brokersApi = {
  list: () => apiClient.get('/api/brokers'),
  available: () => apiClient.get('/api/brokers/available'),
  connect: (data) => apiClient.post('/api/brokers/connect', data),
  test: (name) => apiClient.get(`/api/brokers/${name}/test`),
};

export const settingsApi = {
  get: () => apiClient.get('/api/settings'),
  patchAllocation: (data) => apiClient.post('/api/settings/allocation', data),
  changePassword: (data) => apiClient.post('/api/settings/vault-password', data),
};
```

- [ ] **Step 2: Verify no lint errors**

```bash
cd frontend && npm run lint -- --max-warnings=0 2>&1 | tail -5
```

Expected: exit 0 or only pre-existing warnings.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils/api-client.js
git commit -m "feat(4D.1): Add brokersApi + settingsApi to api-client"
```

---

## Task 2: Zustand Store — `controlRoom.store.js`

**Files:**
- Create: `frontend/src/stores/controlRoom.store.js`
- Create: `frontend/src/stores/__tests__/controlRoom.store.test.js`

**Interfaces:**
- Consumes: `brokersApi`, `llmApi`, `agentsApi`, `settingsApi` from `../utils/api-client`
- Produces: `useControlRoomStore` default export with state: `{ brokers, availableBrokers, llmConfig, agents, settings, loading, error, saving }` and actions: `fetchAll()`, `fetchBrokers()`, `fetchLLM()`, `fetchAgents()`, `fetchSettings()`, `connectBroker(data)`, `testBroker(name)`, `patchLLM(data)`, `testLLM()`, `startAgent(id)`, `stopAgent(id)`, `pauseAgent(id)`, `saveAllocation(data)`, `changePassword(data)`

- [ ] **Step 1: Write failing test**

Create `frontend/src/stores/__tests__/controlRoom.store.test.js`:

```js
import { renderHook, act } from '@testing-library/react';
import useControlRoomStore from '../controlRoom.store';
import { brokersApi, llmApi, agentsApi, settingsApi } from '../../utils/api-client';

jest.mock('../../utils/api-client', () => ({
  brokersApi: {
    list: jest.fn(),
    available: jest.fn(),
    connect: jest.fn(),
    test: jest.fn(),
  },
  llmApi: {
    getConfig: jest.fn(),
    patchConfig: jest.fn(),
    test: jest.fn(),
  },
  agentsApi: {
    list: jest.fn(),
    start: jest.fn(),
    stop: jest.fn(),
    pause: jest.fn(),
  },
  settingsApi: {
    get: jest.fn(),
    patchAllocation: jest.fn(),
    changePassword: jest.fn(),
  },
}));

beforeEach(() => {
  jest.clearAllMocks();
  // reset store between tests
  useControlRoomStore.setState({
    brokers: [], availableBrokers: [], llmConfig: null,
    agents: [], settings: null, loading: false, error: null, saving: false,
  });
});

test('fetchBrokers sets brokers and availableBrokers', async () => {
  brokersApi.list.mockResolvedValue([{ broker_name: 'alpaca', is_active: true }]);
  brokersApi.available.mockResolvedValue({ brokers: ['alpaca', 'binance'] });

  const { result } = renderHook(() => useControlRoomStore());
  await act(async () => { await result.current.fetchBrokers(); });

  expect(result.current.brokers).toEqual([{ broker_name: 'alpaca', is_active: true }]);
  expect(result.current.availableBrokers).toEqual(['alpaca', 'binance']);
  expect(result.current.loading).toBe(false);
  expect(result.current.error).toBeNull();
});

test('fetchBrokers sets error on failure', async () => {
  brokersApi.list.mockRejectedValue(new Error('network error'));
  brokersApi.available.mockResolvedValue({ brokers: [] });

  const { result } = renderHook(() => useControlRoomStore());
  await act(async () => { await result.current.fetchBrokers(); });

  expect(result.current.error).toBe('network error');
  expect(result.current.loading).toBe(false);
});

test('startAgent updates agent status in state', async () => {
  agentsApi.start.mockResolvedValue({ id: '1', status: 'running' });
  useControlRoomStore.setState({ agents: [{ id: '1', status: 'stopped', name: 'A' }] });

  const { result } = renderHook(() => useControlRoomStore());
  await act(async () => { await result.current.startAgent('1'); });

  expect(result.current.agents[0].status).toBe('running');
});

test('saveAllocation calls settingsApi.patchAllocation and sets saving false', async () => {
  settingsApi.patchAllocation.mockResolvedValue({ status: 'updated' });

  const { result } = renderHook(() => useControlRoomStore());
  await act(async () => {
    await result.current.saveAllocation({ max_portfolio_drawdown: 0.2, default_position_size: 0.05, max_agents: 20 });
  });

  expect(settingsApi.patchAllocation).toHaveBeenCalledWith({ max_portfolio_drawdown: 0.2, default_position_size: 0.05, max_agents: 20 });
  expect(result.current.saving).toBe(false);
});

test('testLLM returns result from llmApi.test', async () => {
  llmApi.test.mockResolvedValue({ ok: true, latency_ms: 120 });

  const { result } = renderHook(() => useControlRoomStore());
  let res;
  await act(async () => { res = await result.current.testLLM(); });

  expect(res).toEqual({ ok: true, latency_ms: 120 });
});
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd frontend && npm test -- --watchAll=false --testPathPattern="controlRoom.store" 2>&1 | tail -15
```

Expected: FAIL — `Cannot find module '../controlRoom.store'`

- [ ] **Step 3: Create the store**

Create `frontend/src/stores/controlRoom.store.js`:

```js
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { brokersApi, llmApi, agentsApi, settingsApi } from '../utils/api-client';

const useControlRoomStore = create(devtools((set, get) => ({
  brokers: [],
  availableBrokers: [],
  llmConfig: null,
  agents: [],
  settings: null,
  loading: false,
  error: null,
  saving: false,

  fetchBrokers: async () => {
    set({ loading: true, error: null });
    try {
      const [list, avail] = await Promise.all([brokersApi.list(), brokersApi.available()]);
      set({ brokers: list, availableBrokers: avail.brokers ?? [], loading: false });
    } catch (err) {
      set({ loading: false, error: err.message });
    }
  },

  fetchLLM: async () => {
    set({ loading: true, error: null });
    try {
      const data = await llmApi.getConfig();
      set({ llmConfig: data, loading: false });
    } catch (err) {
      set({ loading: false, error: err.message });
    }
  },

  fetchAgents: async () => {
    set({ loading: true, error: null });
    try {
      const data = await agentsApi.list();
      set({ agents: Array.isArray(data) ? data : data?.items ?? [], loading: false });
    } catch (err) {
      set({ loading: false, error: err.message });
    }
  },

  fetchSettings: async () => {
    set({ loading: true, error: null });
    try {
      const data = await settingsApi.get();
      set({ settings: data, loading: false });
    } catch (err) {
      set({ loading: false, error: err.message });
    }
  },

  fetchAll: async () => {
    const { fetchBrokers, fetchLLM, fetchAgents, fetchSettings } = get();
    await Promise.allSettled([fetchBrokers(), fetchLLM(), fetchAgents(), fetchSettings()]);
  },

  connectBroker: async (data) => {
    set({ saving: true, error: null });
    try {
      const broker = await brokersApi.connect(data);
      set((s) => ({
        brokers: s.brokers.some((b) => b.broker_name === broker.broker_name)
          ? s.brokers.map((b) => b.broker_name === broker.broker_name ? broker : b)
          : [...s.brokers, broker],
        saving: false,
      }));
    } catch (err) {
      set({ saving: false, error: err.message });
      throw err;
    }
  },

  testBroker: async (name) => {
    try {
      return await brokersApi.test(name);
    } catch (err) {
      return { connected: false, message: err.message };
    }
  },

  patchLLM: async (data) => {
    set({ saving: true, error: null });
    try {
      const updated = await llmApi.patchConfig(data);
      set({ llmConfig: { ...get().llmConfig, ...updated }, saving: false });
    } catch (err) {
      set({ saving: false, error: err.message });
      throw err;
    }
  },

  testLLM: async () => {
    try {
      return await llmApi.test();
    } catch (err) {
      return { ok: false, latency_ms: 0, error: err.message };
    }
  },

  startAgent: async (id) => {
    try {
      const updated = await agentsApi.start(id);
      set((s) => ({ agents: s.agents.map((a) => a.id === id ? { ...a, ...updated } : a) }));
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  stopAgent: async (id) => {
    try {
      const updated = await agentsApi.stop(id);
      set((s) => ({ agents: s.agents.map((a) => a.id === id ? { ...a, ...updated } : a) }));
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  pauseAgent: async (id) => {
    try {
      const updated = await agentsApi.pause(id);
      set((s) => ({ agents: s.agents.map((a) => a.id === id ? { ...a, ...updated } : a) }));
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  saveAllocation: async (data) => {
    set({ saving: true, error: null });
    try {
      await settingsApi.patchAllocation(data);
      set((s) => ({ settings: { ...s.settings, allocation: { ...s.settings?.allocation, ...data } }, saving: false }));
    } catch (err) {
      set({ saving: false, error: err.message });
      throw err;
    }
  },

  changePassword: async (data) => {
    set({ saving: true, error: null });
    try {
      const res = await settingsApi.changePassword(data);
      set({ saving: false });
      return res;
    } catch (err) {
      set({ saving: false, error: err.message });
      throw err;
    }
  },

  clearError: () => set({ error: null }),
}), { name: 'control-room-store' }));

export default useControlRoomStore;
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd frontend && npm test -- --watchAll=false --testPathPattern="controlRoom.store" 2>&1 | tail -15
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/controlRoom.store.js frontend/src/stores/__tests__/controlRoom.store.test.js
git commit -m "feat(4D.2): Add controlRoom.store with all section actions + tests"
```

---

## Task 3: BrokerSection Component

**Files:**
- Create: `frontend/src/components/ControlRoom/BrokerSection.jsx`

**Interfaces:**
- Consumes: `useControlRoomStore` — `brokers`, `availableBrokers`, `loading`, `saving`, `error`, `connectBroker(data)`, `testBroker(name)`
- Produces: `<BrokerSection />` — no props

- [ ] **Step 1: Create BrokerSection.jsx**

Create `frontend/src/components/ControlRoom/BrokerSection.jsx`:

```jsx
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Button } from '../Common/Button';
import { Spinner } from '../Common/Spinner';
import useControlRoomStore from '../../stores/controlRoom.store';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  marginBottom: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const input = {
  background: 'var(--color-bg-elevated)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-sm)',
  padding: 'var(--space-2) var(--space-3)',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
  width: '100%',
  boxSizing: 'border-box',
};

export default function BrokerSection() {
  const { brokers, availableBrokers, loading, saving, connectBroker, testBroker } = useControlRoomStore();
  const [form, setForm] = useState({ broker_name: '', api_key: '', secret: '', is_paper: true });
  const [testResults, setTestResults] = useState({});
  const [formError, setFormError] = useState(null);

  const handleConnect = async (e) => {
    e.preventDefault();
    setFormError(null);
    try {
      await connectBroker(form);
      setForm({ broker_name: '', api_key: '', secret: '', is_paper: true });
    } catch (err) {
      setFormError(err.message);
    }
  };

  const handleTest = async (name) => {
    const res = await testBroker(name);
    setTestResults((prev) => ({ ...prev, [name]: res }));
  };

  if (loading && brokers.length === 0) {
    return <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}><Spinner /></div>;
  }

  return (
    <div>
      {/* Connected brokers */}
      <div style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)', letterSpacing: '0.08em' }}>
          CONNECTED BROKERS
        </div>
        {brokers.length === 0 ? (
          <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No brokers connected</div>
        ) : (
          brokers.map((b) => (
            <motion.div key={b.broker_name} initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ color: b.is_active ? 'var(--color-accent-primary)' : 'var(--color-text-muted)', marginRight: 'var(--space-2)' }}>
                    {b.is_active ? '●' : '○'}
                  </span>
                  <span style={{ color: 'var(--color-text-primary)', textTransform: 'uppercase' }}>{b.broker_name}</span>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
                  {testResults[b.broker_name] && (
                    <span style={{ fontSize: 'var(--font-size-xs)', color: testResults[b.broker_name].connected ? 'var(--color-accent-primary)' : 'var(--color-accent-danger)' }}>
                      {testResults[b.broker_name].connected ? '✓ OK' : '✗ FAIL'}
                    </span>
                  )}
                  <Button variant="ghost" onClick={() => handleTest(b.broker_name)}>Test</Button>
                </div>
              </div>
              {b.connected_at && (
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-2)' }}>
                  Connected {new Date(b.connected_at).toLocaleDateString()}
                </div>
              )}
            </motion.div>
          ))
        )}
      </div>

      {/* Add broker form */}
      <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)', letterSpacing: '0.08em' }}>
        ADD BROKER
      </div>
      <form onSubmit={handleConnect} style={{ ...card, display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <select
          value={form.broker_name}
          onChange={(e) => setForm((f) => ({ ...f, broker_name: e.target.value }))}
          style={{ ...input }}
          required
        >
          <option value="">Select broker…</option>
          {availableBrokers.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="API Key"
          value={form.api_key}
          onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
          style={input}
          required
          autoComplete="off"
        />
        <input
          type="password"
          placeholder="Secret"
          value={form.secret}
          onChange={(e) => setForm((f) => ({ ...f, secret: e.target.value }))}
          style={input}
          required
          autoComplete="new-password"
        />
        <label style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={form.is_paper}
            onChange={(e) => setForm((f) => ({ ...f, is_paper: e.target.checked }))}
          />
          Paper trading mode
        </label>
        {formError && <div style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)' }}>{formError}</div>}
        <Button type="submit" disabled={saving || !form.broker_name}>
          {saving ? 'Connecting…' : 'Connect Broker'}
        </Button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Verify no lint errors**

```bash
cd frontend && npm run lint -- --max-warnings=0 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ControlRoom/BrokerSection.jsx
git commit -m "feat(4D.3): Add BrokerSection component"
```

---

## Task 4: LLMSection Component

**Files:**
- Create: `frontend/src/components/ControlRoom/LLMSection.jsx`

**Interfaces:**
- Consumes: `useControlRoomStore` — `llmConfig`, `saving`, `patchLLM(data)`, `testLLM()`
- Produces: `<LLMSection />` — no props

- [ ] **Step 1: Create LLMSection.jsx**

Create `frontend/src/components/ControlRoom/LLMSection.jsx`:

```jsx
import React, { useState } from 'react';
import { Button } from '../Common/Button';
import { Spinner } from '../Common/Spinner';
import useControlRoomStore from '../../stores/controlRoom.store';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  marginBottom: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const input = {
  background: 'var(--color-bg-elevated)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-sm)',
  padding: 'var(--space-2) var(--space-3)',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
  width: '100%',
  boxSizing: 'border-box',
};

const PROVIDERS = ['ollama', 'claude', 'openai'];
const OLLAMA_MODELS = ['mistral', 'llama3', 'codellama', 'gemma'];
const CLAUDE_MODELS = ['claude-sonnet-4-6', 'claude-haiku-4-5-20251001'];
const OPENAI_MODELS = ['gpt-4o', 'gpt-4o-mini'];

function modelsFor(provider) {
  if (provider === 'ollama') return OLLAMA_MODELS;
  if (provider === 'claude') return CLAUDE_MODELS;
  if (provider === 'openai') return OPENAI_MODELS;
  return [];
}

export default function LLMSection() {
  const { llmConfig, loading, saving, patchLLM, testLLM } = useControlRoomStore();
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);
  const [patchError, setPatchError] = useState(null);

  if (loading && !llmConfig) {
    return <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}><Spinner /></div>;
  }

  if (!llmConfig) {
    return <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>LLM config unavailable</div>;
  }

  const handleProvider = async (provider) => {
    setPatchError(null);
    try {
      await patchLLM({ provider });
    } catch (err) {
      setPatchError(err.message);
    }
  };

  const handleModel = async (model) => {
    setPatchError(null);
    try {
      await patchLLM({ model });
    } catch (err) {
      setPatchError(err.message);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    const res = await testLLM();
    setTestResult(res);
    setTesting(false);
  };

  return (
    <div>
      {/* Provider toggle */}
      <div style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)', letterSpacing: '0.08em' }}>
          PROVIDER
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          {PROVIDERS.map((p) => (
            <Button
              key={p}
              variant={llmConfig.provider === p ? 'primary' : 'ghost'}
              onClick={() => handleProvider(p)}
              disabled={saving}
            >
              {p}
            </Button>
          ))}
        </div>
        {llmConfig.provider === 'claude' && !llmConfig.has_claude_key && (
          <div style={{ color: 'var(--color-accent-warning)', fontSize: 'var(--font-size-xs)', marginTop: 'var(--space-2)' }}>
            ⚠ anthropic_api_key not in vault — save it in Vault &amp; Security tab first
          </div>
        )}
        {llmConfig.provider === 'openai' && !llmConfig.has_openai_key && (
          <div style={{ color: 'var(--color-accent-warning)', fontSize: 'var(--font-size-xs)', marginTop: 'var(--space-2)' }}>
            ⚠ openai_api_key not in vault — save it in Vault &amp; Security tab first
          </div>
        )}
      </div>

      {/* Model selector */}
      <div style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)', letterSpacing: '0.08em' }}>
          MODEL
        </div>
        <select
          value={llmConfig.model}
          onChange={(e) => handleModel(e.target.value)}
          disabled={saving}
          style={{ ...input, width: 'auto', minWidth: 240 }}
        >
          {modelsFor(llmConfig.provider).map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      {/* Ollama URL (shown only for ollama) */}
      {llmConfig.provider === 'ollama' && (
        <div style={{ marginBottom: 'var(--space-6)' }}>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)', letterSpacing: '0.08em' }}>
            OLLAMA URL
          </div>
          <input
            type="text"
            defaultValue={llmConfig.ollama_url}
            onBlur={(e) => patchLLM({ ollama_url: e.target.value })}
            style={{ ...input, width: 300 }}
          />
        </div>
      )}

      {/* Status + test */}
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
              Active: </span>
            <span style={{ color: 'var(--color-accent-primary)' }}>{llmConfig.provider}/{llmConfig.model}</span>
          </div>
          <Button variant="ghost" onClick={handleTest} disabled={testing}>
            {testing ? 'Testing…' : 'Test Connection'}
          </Button>
        </div>
        {testResult && (
          <div style={{ marginTop: 'var(--space-3)', fontSize: 'var(--font-size-sm)' }}>
            {testResult.ok ? (
              <span style={{ color: 'var(--color-accent-primary)' }}>✓ OK — {testResult.latency_ms}ms</span>
            ) : (
              <span style={{ color: 'var(--color-accent-danger)' }}>✗ {testResult.error ?? 'Failed'}</span>
            )}
          </div>
        )}
      </div>

      {patchError && <div style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', marginTop: 'var(--space-2)' }}>{patchError}</div>}
    </div>
  );
}
```

- [ ] **Step 2: Lint check**

```bash
cd frontend && npm run lint -- --max-warnings=0 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ControlRoom/LLMSection.jsx
git commit -m "feat(4D.4): Add LLMSection component"
```

---

## Task 5: AllocationSection Component

**Files:**
- Create: `frontend/src/components/ControlRoom/AllocationSection.jsx`

**Interfaces:**
- Consumes: `useControlRoomStore` — `settings`, `loading`, `saving`, `saveAllocation(data)`
- Produces: `<AllocationSection />` — no props

- [ ] **Step 1: Create AllocationSection.jsx**

Create `frontend/src/components/ControlRoom/AllocationSection.jsx`:

```jsx
import React, { useState, useEffect } from 'react';
import { Button } from '../Common/Button';
import { Spinner } from '../Common/Spinner';
import useControlRoomStore from '../../stores/controlRoom.store';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const label = {
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--space-2)',
  marginBottom: 'var(--space-4)',
};

export default function AllocationSection() {
  const { settings, loading, saving, saveAllocation } = useControlRoomStore();
  const alloc = settings?.allocation;

  const [form, setForm] = useState({
    max_portfolio_drawdown: 0.25,
    default_position_size: 0.05,
    max_agents: 20,
  });
  const [saveError, setSaveError] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (alloc) {
      setForm({
        max_portfolio_drawdown: alloc.max_portfolio_drawdown ?? 0.25,
        default_position_size: alloc.default_position_size ?? 0.05,
        max_agents: alloc.max_agents ?? 20,
      });
    }
  }, [alloc]);

  if (loading && !settings) {
    return <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}><Spinner /></div>;
  }

  const handleSave = async (e) => {
    e.preventDefault();
    setSaveError(null);
    setSaved(false);
    try {
      await saveAllocation(form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setSaveError(err.message);
    }
  };

  const pct = (v) => `${(v * 100).toFixed(0)}%`;

  return (
    <form onSubmit={handleSave} style={card}>
      <div style={label}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', letterSpacing: '0.08em' }}>
            MAX PORTFOLIO DRAWDOWN
          </span>
          <span style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)' }}>
            {pct(form.max_portfolio_drawdown)}
          </span>
        </div>
        <input
          type="range"
          min="0.05"
          max="0.50"
          step="0.01"
          value={form.max_portfolio_drawdown}
          onChange={(e) => setForm((f) => ({ ...f, max_portfolio_drawdown: parseFloat(e.target.value) }))}
          style={{ width: '100%', accentColor: 'var(--color-accent-danger)' }}
        />
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
          All agents auto-pause when portfolio drawdown exceeds this limit
        </div>
      </div>

      <div style={label}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', letterSpacing: '0.08em' }}>
            DEFAULT POSITION SIZE
          </span>
          <span style={{ color: 'var(--color-accent-secondary)', fontSize: 'var(--font-size-sm)' }}>
            {pct(form.default_position_size)}
          </span>
        </div>
        <input
          type="range"
          min="0.01"
          max="0.20"
          step="0.01"
          value={form.default_position_size}
          onChange={(e) => setForm((f) => ({ ...f, default_position_size: parseFloat(e.target.value) }))}
          style={{ width: '100%', accentColor: 'var(--color-accent-secondary)' }}
        />
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
          Per-trade position size as % of portfolio (agents may override)
        </div>
      </div>

      <div style={label}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', letterSpacing: '0.08em' }}>
            MAX AGENTS
          </span>
          <span style={{ color: 'var(--color-text-primary)', fontSize: 'var(--font-size-sm)' }}>
            {form.max_agents}
          </span>
        </div>
        <input
          type="range"
          min="1"
          max="50"
          step="1"
          value={form.max_agents}
          onChange={(e) => setForm((f) => ({ ...f, max_agents: parseInt(e.target.value) }))}
          style={{ width: '100%', accentColor: 'var(--color-accent-primary)' }}
        />
      </div>

      {saveError && <div style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)' }}>{saveError}</div>}
      {saved && <div style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)' }}>✓ Saved</div>}

      <Button type="submit" disabled={saving}>
        {saving ? 'Saving…' : 'Save Allocation Settings'}
      </Button>
    </form>
  );
}
```

- [ ] **Step 2: Lint check**

```bash
cd frontend && npm run lint -- --max-warnings=0 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ControlRoom/AllocationSection.jsx
git commit -m "feat(4D.5): Add AllocationSection component"
```

---

## Task 6: AgentManagementSection Component

**Files:**
- Create: `frontend/src/components/ControlRoom/AgentManagementSection.jsx`

**Interfaces:**
- Consumes: `useControlRoomStore` — `agents`, `loading`, `startAgent(id)`, `stopAgent(id)`, `pauseAgent(id)`
- Produces: `<AgentManagementSection />` — no props

- [ ] **Step 1: Create AgentManagementSection.jsx**

Create `frontend/src/components/ControlRoom/AgentManagementSection.jsx`:

```jsx
import React, { useState } from 'react';
import { Button } from '../Common/Button';
import { Spinner } from '../Common/Spinner';
import useControlRoomStore from '../../stores/controlRoom.store';

const row = {
  display: 'grid',
  gridTemplateColumns: '1fr 120px 80px 100px 160px',
  alignItems: 'center',
  gap: 'var(--space-3)',
  padding: 'var(--space-3) var(--space-4)',
  borderBottom: '1px solid var(--color-border-subtle)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
};

const STATUS_COLOR = {
  running: 'var(--color-agent-running)',
  idle: 'var(--color-agent-idle)',
  paused: 'var(--color-agent-paused)',
  error: 'var(--color-agent-error)',
  stopped: 'var(--color-agent-stopped)',
};

export default function AgentManagementSection() {
  const { agents, loading, startAgent, stopAgent, pauseAgent } = useControlRoomStore();
  const [actionError, setActionError] = useState(null);
  const [busyIds, setBusyIds] = useState(new Set());

  if (loading && agents.length === 0) {
    return <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}><Spinner /></div>;
  }

  const withBusy = (id, fn) => async () => {
    setBusyIds((s) => new Set([...s, id]));
    setActionError(null);
    try {
      await fn(id);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusyIds((s) => { const n = new Set(s); n.delete(id); return n; });
    }
  };

  const pnlColor = (v) => (v ?? 0) >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)';

  return (
    <div style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ ...row, background: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-xs)', letterSpacing: '0.08em', borderBottom: '1px solid var(--color-border)' }}>
        <div>AGENT</div>
        <div>STATUS</div>
        <div>P&L</div>
        <div>CONF</div>
        <div>ACTIONS</div>
      </div>

      {agents.length === 0 ? (
        <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
          No agents
        </div>
      ) : (
        agents.map((agent) => {
          const busy = busyIds.has(agent.id);
          const pnl = agent.total_pnl ?? 0;
          const conf = agent.confidence_score ?? 0;
          const color = STATUS_COLOR[agent.status] ?? 'var(--color-text-muted)';
          return (
            <div key={agent.id} style={row}>
              <div style={{ color: 'var(--color-text-primary)' }}>{agent.name}</div>
              <div style={{ color }}>{agent.status}</div>
              <div style={{ color: pnlColor(pnl) }}>{pnl >= 0 ? '+' : ''}{pnl.toFixed(0)}</div>
              <div style={{ color: conf >= 70 ? 'var(--color-accent-primary)' : conf >= 50 ? 'var(--color-accent-warning)' : 'var(--color-accent-danger)' }}>
                {conf}%
              </div>
              <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
                {busy ? (
                  <Spinner size={14} />
                ) : (
                  <>
                    {agent.status !== 'running' && (
                      <Button variant="primary" onClick={withBusy(agent.id, startAgent)} style={{ padding: '2px 8px', fontSize: '0.65rem' }}>
                        Start
                      </Button>
                    )}
                    {agent.status === 'running' && (
                      <Button variant="ghost" onClick={withBusy(agent.id, pauseAgent)} style={{ padding: '2px 8px', fontSize: '0.65rem' }}>
                        Pause
                      </Button>
                    )}
                    {agent.status !== 'stopped' && (
                      <Button variant="danger" onClick={withBusy(agent.id, stopAgent)} style={{ padding: '2px 8px', fontSize: '0.65rem' }}>
                        Stop
                      </Button>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })
      )}

      {actionError && (
        <div style={{ padding: 'var(--space-3) var(--space-4)', color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', borderTop: '1px solid var(--color-border)' }}>
          {actionError}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Lint check**

```bash
cd frontend && npm run lint -- --max-warnings=0 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ControlRoom/AgentManagementSection.jsx
git commit -m "feat(4D.6): Add AgentManagementSection component"
```

---

## Task 7: RiskSection Component

**Files:**
- Create: `frontend/src/components/ControlRoom/RiskSection.jsx`

**Interfaces:**
- Consumes: `useControlRoomStore` — `settings`, `loading`, `saving`, `saveAllocation(data)` (reuses same endpoint; `max_portfolio_drawdown` + `default_position_size` + `max_agents` are all in `/api/settings/allocation`)
- Produces: `<RiskSection />` — no props

- [ ] **Step 1: Create RiskSection.jsx**

Create `frontend/src/components/ControlRoom/RiskSection.jsx`:

```jsx
import React, { useState, useEffect } from 'react';
import { Button } from '../Common/Button';
import { Spinner } from '../Common/Spinner';
import useControlRoomStore from '../../stores/controlRoom.store';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const row = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: 'var(--space-3) 0',
  borderBottom: '1px solid var(--color-border-subtle)',
};

export default function RiskSection() {
  const { settings, loading, saving, saveAllocation } = useControlRoomStore();
  const alloc = settings?.allocation;

  const [drawdown, setDrawdown] = useState(0.25);
  const [posSize, setPosSize] = useState(0.05);
  const [maxAgents, setMaxAgents] = useState(20);
  const [saveError, setSaveError] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (alloc) {
      setDrawdown(alloc.max_portfolio_drawdown ?? 0.25);
      setPosSize(alloc.default_position_size ?? 0.05);
      setMaxAgents(alloc.max_agents ?? 20);
    }
  }, [alloc]);

  if (loading && !settings) {
    return <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}><Spinner /></div>;
  }

  const handleSave = async (e) => {
    e.preventDefault();
    setSaveError(null);
    setSaved(false);
    try {
      await saveAllocation({ max_portfolio_drawdown: drawdown, default_position_size: posSize, max_agents: maxAgents });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setSaveError(err.message);
    }
  };

  const pct = (v) => `${(v * 100).toFixed(0)}%`;

  return (
    <form onSubmit={handleSave} style={card}>
      {/* Current values summary */}
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-xs)', letterSpacing: '0.08em', marginBottom: 'var(--space-3)' }}>
          CURRENT RISK PARAMETERS
        </div>
        <div style={row}>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>Hard Drawdown Limit</span>
          <span style={{ color: 'var(--color-accent-danger)' }}>{pct(drawdown)}</span>
        </div>
        <div style={row}>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>Default Position Size</span>
          <span style={{ color: 'var(--color-accent-secondary)' }}>{pct(posSize)}</span>
        </div>
        <div style={{ ...row, borderBottom: 'none' }}>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>Max Concurrent Agents</span>
          <span style={{ color: 'var(--color-text-primary)' }}>{maxAgents}</span>
        </div>
      </div>

      {/* Edit */}
      <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-xs)', letterSpacing: '0.08em', marginBottom: 'var(--space-3)' }}>
        ADJUST
      </div>

      <div style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-1)' }}>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>Drawdown limit</span>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-accent-danger)' }}>{pct(drawdown)}</span>
        </div>
        <input type="range" min="0.05" max="0.50" step="0.01" value={drawdown}
          onChange={(e) => setDrawdown(parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--color-accent-danger)' }} />
      </div>

      <div style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-1)' }}>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>Position size</span>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-accent-secondary)' }}>{pct(posSize)}</span>
        </div>
        <input type="range" min="0.01" max="0.20" step="0.01" value={posSize}
          onChange={(e) => setPosSize(parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--color-accent-secondary)' }} />
      </div>

      <div style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-1)' }}>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>Max agents</span>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>{maxAgents}</span>
        </div>
        <input type="range" min="1" max="50" step="1" value={maxAgents}
          onChange={(e) => setMaxAgents(parseInt(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--color-accent-primary)' }} />
      </div>

      {saveError && <div style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)' }}>{saveError}</div>}
      {saved && <div style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)' }}>✓ Saved</div>}

      <Button type="submit" disabled={saving}>
        {saving ? 'Saving…' : 'Save Risk Settings'}
      </Button>
    </form>
  );
}
```

- [ ] **Step 2: Lint check**

```bash
cd frontend && npm run lint -- --max-warnings=0 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ControlRoom/RiskSection.jsx
git commit -m "feat(4D.7): Add RiskSection component"
```

---

## Task 8: VaultSection Component

**Files:**
- Create: `frontend/src/components/ControlRoom/VaultSection.jsx`

**Interfaces:**
- Consumes: `useControlRoomStore` — `saving`, `changePassword(data)`. Also calls `vaultApi.listKeys()` and `vaultApi.deleteKey(key)` directly (vault state not in controlRoom store — one-off reads don't need store).
- Produces: `<VaultSection />` — no props

- [ ] **Step 1: Create VaultSection.jsx**

Create `frontend/src/components/ControlRoom/VaultSection.jsx`:

```jsx
import React, { useState, useEffect } from 'react';
import { Button } from '../Common/Button';
import { Spinner } from '../Common/Spinner';
import useControlRoomStore from '../../stores/controlRoom.store';
import { vaultApi } from '../../utils/api-client';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  marginBottom: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const input = {
  background: 'var(--color-bg-elevated)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-sm)',
  padding: 'var(--space-2) var(--space-3)',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
  width: '100%',
  boxSizing: 'border-box',
};

export default function VaultSection() {
  const { saving, changePassword } = useControlRoomStore();

  const [keys, setKeys] = useState([]);
  const [keysLoading, setKeysLoading] = useState(true);
  const [keysError, setKeysError] = useState(null);

  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [pwError, setPwError] = useState(null);
  const [pwSuccess, setPwSuccess] = useState(false);

  useEffect(() => {
    vaultApi.listKeys()
      .then((data) => { setKeys(Array.isArray(data) ? data : []); setKeysLoading(false); })
      .catch((err) => { setKeysError(err.message); setKeysLoading(false); });
  }, []);

  const handleDeleteKey = async (key) => {
    try {
      await vaultApi.deleteKey(key);
      setKeys((ks) => ks.filter((k) => k !== key));
    } catch (err) {
      setKeysError(err.message);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwError(null);
    setPwSuccess(false);
    if (pwForm.new_password !== pwForm.confirm) {
      setPwError('New passwords do not match');
      return;
    }
    if (pwForm.new_password.length < 8) {
      setPwError('New password must be at least 8 characters');
      return;
    }
    try {
      await changePassword({ current_password: pwForm.current_password, new_password: pwForm.new_password });
      setPwSuccess(true);
      setPwForm({ current_password: '', new_password: '', confirm: '' });
    } catch (err) {
      setPwError(err.message);
    }
  };

  return (
    <div>
      {/* Vault keys */}
      <div style={{ marginBottom: 'var(--space-2)', color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', letterSpacing: '0.08em' }}>
        STORED KEYS
      </div>
      <div style={card}>
        {keysLoading ? (
          <Spinner />
        ) : keysError ? (
          <div style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)' }}>{keysError}</div>
        ) : keys.length === 0 ? (
          <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No keys in vault</div>
        ) : (
          keys.map((key) => (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--space-2) 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
              <span style={{ color: 'var(--color-text-primary)', fontSize: 'var(--font-size-sm)' }}>
                🔑 {key}
              </span>
              <Button variant="danger" onClick={() => handleDeleteKey(key)} style={{ padding: '2px 8px', fontSize: '0.65rem' }}>
                Delete
              </Button>
            </div>
          ))
        )}
      </div>

      {/* Change password */}
      <div style={{ marginBottom: 'var(--space-2)', color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', letterSpacing: '0.08em' }}>
        CHANGE VAULT PASSWORD
      </div>
      <form onSubmit={handleChangePassword} style={{ ...card, display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <input
          type="password"
          placeholder="Current password"
          value={pwForm.current_password}
          onChange={(e) => setPwForm((f) => ({ ...f, current_password: e.target.value }))}
          style={input}
          required
          autoComplete="current-password"
        />
        <input
          type="password"
          placeholder="New password (min 8 chars)"
          value={pwForm.new_password}
          onChange={(e) => setPwForm((f) => ({ ...f, new_password: e.target.value }))}
          style={input}
          required
          autoComplete="new-password"
        />
        <input
          type="password"
          placeholder="Confirm new password"
          value={pwForm.confirm}
          onChange={(e) => setPwForm((f) => ({ ...f, confirm: e.target.value }))}
          style={input}
          required
          autoComplete="new-password"
        />
        {pwError && <div style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)' }}>{pwError}</div>}
        {pwSuccess && <div style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-sm)' }}>✓ Password changed</div>}
        <Button type="submit" disabled={saving}>
          {saving ? 'Changing…' : 'Change Password'}
        </Button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Lint check**

```bash
cd frontend && npm run lint -- --max-warnings=0 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ControlRoom/VaultSection.jsx
git commit -m "feat(4D.8): Add VaultSection component"
```

---

## Task 9: Barrel Export + ControlRoom.jsx

**Files:**
- Create: `frontend/src/components/ControlRoom/index.js`
- Modify: `frontend/src/pages/ControlRoom.jsx`

**Interfaces:**
- Consumes: all 6 section components, `useControlRoomStore`
- Produces: final `ControlRoom` page replacing placeholder

- [ ] **Step 1: Create barrel index.js**

Create `frontend/src/components/ControlRoom/index.js`:

```js
export { default as BrokerSection } from './BrokerSection';
export { default as LLMSection } from './LLMSection';
export { default as AllocationSection } from './AllocationSection';
export { default as AgentManagementSection } from './AgentManagementSection';
export { default as RiskSection } from './RiskSection';
export { default as VaultSection } from './VaultSection';
```

- [ ] **Step 2: Replace ControlRoom.jsx**

Replace the entire contents of `frontend/src/pages/ControlRoom.jsx`:

```jsx
import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import useControlRoomStore from '../stores/controlRoom.store';
import {
  BrokerSection,
  LLMSection,
  AllocationSection,
  AgentManagementSection,
  RiskSection,
  VaultSection,
} from '../components/ControlRoom';

const TABS = [
  { key: 'brokers',    label: 'Brokers' },
  { key: 'llm',        label: 'LLM' },
  { key: 'allocation', label: 'Allocation' },
  { key: 'agents',     label: 'Agents' },
  { key: 'risk',       label: 'Risk' },
  { key: 'vault',      label: 'Vault' },
];

const SECTION = {
  brokers:    <BrokerSection />,
  llm:        <LLMSection />,
  allocation: <AllocationSection />,
  agents:     <AgentManagementSection />,
  risk:       <RiskSection />,
  vault:      <VaultSection />,
};

export default function ControlRoom() {
  const [activeTab, setActiveTab] = useState('brokers');
  const { fetchAll, error, clearError } = useControlRoomStore();

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'var(--color-bg-primary)',
      fontFamily: 'var(--font-mono)',
    }}>
      {/* Tab bar */}
      <div style={{
        display: 'flex',
        gap: 0,
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-bg-secondary)',
        padding: '0 var(--space-4)',
        flexShrink: 0,
      }}>
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: 'var(--space-3) var(--space-4)',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid var(--color-accent-primary)' : '2px solid transparent',
              color: activeTab === tab.key ? 'var(--color-accent-primary)' : 'var(--color-text-secondary)',
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--font-size-sm)',
              cursor: 'pointer',
              letterSpacing: '0.05em',
              transition: 'color var(--transition-fast)',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Global error banner */}
      {error && (
        <div style={{
          background: 'var(--color-bg-elevated)',
          borderBottom: '1px solid var(--color-accent-danger)',
          padding: 'var(--space-2) var(--space-4)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-accent-danger)',
        }}>
          <span>⚠ {error}</span>
          <button onClick={clearError} style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: 'var(--font-size-sm)' }}>
            ✕
          </button>
        </div>
      )}

      {/* Section content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-6)' }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { duration: 0.2, ease: 'easeOut' } }}
            exit={{ opacity: 0, transition: { duration: 0.15 } }}
          >
            {SECTION[activeTab]}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Lint check**

```bash
cd frontend && npm run lint -- --max-warnings=0 2>&1 | tail -5
```

- [ ] **Step 4: Run all frontend tests**

```bash
cd frontend && npm test -- --watchAll=false 2>&1 | tail -20
```

Expected: existing tests plus the 5 new store tests all pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ControlRoom/index.js frontend/src/pages/ControlRoom.jsx
git commit -m "feat(4D.9): Wire Control Room page — 6-tab layout with all sections"
```

---

## Self-Review

**Spec coverage:**
- ✅ Broker Connections — list + add form + test button (`BrokerSection`)
- ✅ LLM Configuration — provider toggle + model selector + ollama URL + test (`LLMSection`)
- ✅ Capital Allocation — sliders for drawdown/position size/max agents (`AllocationSection`)
- ✅ Agent Management — table with start/stop/pause per agent (`AgentManagementSection`)
- ✅ Risk Settings — same drawdown/position/agents controls, summary view (`RiskSection`)
- ✅ Vault & Security — key list + delete + change password (`VaultSection`)
- ✅ Tab switch animation — `opacity` only, 0.2s easeOut via `AnimatePresence`
- ✅ All colors via CSS vars
- ✅ Spinner for loading states
- ✅ Error states in danger color
- ✅ Empty states in muted color
- ✅ No new backend endpoints
- ✅ Store tests cover fetch, error path, agent action, saveAllocation, testLLM

**Placeholder scan:** None found. All code blocks complete.

**Type consistency:**
- `connectBroker(data)` called in BrokerSection → defined in store ✅
- `testBroker(name)` → defined in store ✅
- `patchLLM(data)` → defined in store ✅
- `testLLM()` → defined in store ✅
- `startAgent(id)` / `stopAgent(id)` / `pauseAgent(id)` → defined in store ✅
- `saveAllocation(data)` — used in AllocationSection AND RiskSection → same store action ✅
- `changePassword(data)` → defined in store ✅
- `brokersApi` / `settingsApi` — added to api-client.js in Task 1, imported in store ✅
