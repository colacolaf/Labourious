import React, { useState } from 'react';
import useWizardStore from '../../stores/wizard.store';
import { llmApi } from '../../utils/api-client';

const PROVIDERS = ['ollama', 'claude', 'openai'];
const MODELS = {
  ollama: ['mistral', 'llama3', 'codellama', 'phi3'],
  claude: ['claude-sonnet-4-6', 'claude-haiku-4-5-20251001'],
  openai: ['gpt-4o', 'gpt-4o-mini'],
};

export default function LLMStep() {
  const { setFormData, nextStep } = useWizardStore((s) => ({
    setFormData: s.setFormData,
    nextStep: s.nextStep,
  }));
  const [provider, setProvider] = useState('ollama');
  const [model, setModel] = useState(MODELS.ollama[0]);
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function handleProviderChange(p) {
    setProvider(p);
    setModel(MODELS[p][0]);
    setError('');
  }

  async function handleSave() {
    setLoading(true);
    setError('');
    try {
      const payload = { provider, model };
      if (provider === 'ollama') payload.ollama_url = ollamaUrl;
      await llmApi.patchConfig(payload);
      setFormData('llm', payload);
      nextStep();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleSkip() {
    nextStep();
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div>
        <h2 style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', marginBottom: 'var(--space-2)' }}>
          Configure LLM
        </h2>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Choose the AI brain for your agents.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        {PROVIDERS.map((p) => (
          <button
            key={p}
            onClick={() => handleProviderChange(p)}
            style={{
              padding: 'var(--space-2) var(--space-4)',
              background: provider === p ? 'var(--color-accent-primary)' : 'var(--color-bg-tertiary)',
              color: provider === p ? 'var(--color-bg-primary)' : 'var(--color-text-secondary)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--font-size-sm)',
              cursor: 'pointer',
              fontWeight: provider === p ? 700 : 400,
            }}
          >
            {p}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        {provider === 'ollama' && (
          <label style={labelStyle}>
            Ollama URL
            <input
              type="text"
              value={ollamaUrl}
              onChange={(e) => { setOllamaUrl(e.target.value); setError(''); }}
              style={inputStyle}
            />
          </label>
        )}

        <label style={labelStyle}>
          Model
          <select value={model} onChange={(e) => setModel(e.target.value)} style={inputStyle}>
            {MODELS[provider].map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>
      </div>

      {error && <p style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', fontFamily: 'var(--font-mono)' }}>{error}</p>}

      <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
        <button onClick={handleSave} disabled={loading} style={btnPrimary}>
          {loading ? 'Saving…' : 'Save'}
        </button>
        <button onClick={handleSkip} style={btnSecondary}>Skip</button>
      </div>
    </div>
  );
}

const labelStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--space-2)',
  color: 'var(--color-text-secondary)',
  fontSize: 'var(--font-size-sm)',
  fontFamily: 'var(--font-mono)',
};

const inputStyle = {
  padding: 'var(--space-3)',
  background: 'var(--color-bg-tertiary)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-base)',
  outline: 'none',
};

const btnPrimary = {
  padding: 'var(--space-3) var(--space-6)',
  background: 'var(--color-accent-primary)',
  color: 'var(--color-bg-primary)',
  border: 'none',
  borderRadius: 'var(--radius-md)',
  fontFamily: 'var(--font-mono)',
  fontWeight: 700,
  cursor: 'pointer',
  fontSize: 'var(--font-size-sm)',
};

const btnSecondary = {
  padding: 'var(--space-3) var(--space-6)',
  background: 'transparent',
  color: 'var(--color-text-secondary)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  fontFamily: 'var(--font-mono)',
  cursor: 'pointer',
  fontSize: 'var(--font-size-sm)',
};
