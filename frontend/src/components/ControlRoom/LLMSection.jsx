import React, { useEffect, useState } from 'react';
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
  const [ollamaUrl, setOllamaUrl] = useState(llmConfig?.ollama_url ?? 'http://localhost:11434');

  useEffect(() => {
    if (llmConfig?.ollama_url) setOllamaUrl(llmConfig.ollama_url);
  }, [llmConfig?.ollama_url]);

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
            value={ollamaUrl}
            onChange={(e) => setOllamaUrl(e.target.value)}
            onBlur={() => patchLLM({ ollama_url: ollamaUrl }).catch(() => {})}
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
