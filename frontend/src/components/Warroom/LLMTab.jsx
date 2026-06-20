import React, { useState, useEffect } from 'react';
import { llmApi } from '../../utils/api-client';

const mono = { fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' };
const label = { ...mono, fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', letterSpacing: '0.08em' };
const inputStyle = {
  background: 'var(--color-bg-tertiary)',
  border: '1px solid var(--color-border)',
  color: 'var(--color-text-primary)',
  ...mono,
  padding: '5px 8px',
  borderRadius: 'var(--radius-sm)',
  width: '100%',
};
const btn = (accent) => ({
  ...mono,
  background: 'var(--color-bg-elevated)',
  border: `1px solid ${accent}`,
  color: accent,
  padding: '5px 14px',
  borderRadius: 'var(--radius-sm)',
  cursor: 'pointer',
  letterSpacing: '0.08em',
});

const PROVIDERS = [
  { id: 'ollama', label: 'Ollama (Local)', models: ['mistral', 'llama3', 'gemma2'] },
  { id: 'claude', label: 'Claude', models: ['claude-sonnet-4-6', 'claude-haiku-4-5-20251001'] },
  { id: 'openai', label: 'GPT-4o', models: ['gpt-4o', 'gpt-4o-mini'] },
];

export default function LLMTab({ agent }) {
  const [config, setConfig] = useState(null);
  const [selected, setSelected] = useState('ollama');
  const [model, setModel] = useState('mistral');
  const [openaiKey, setOpenaiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [testResult, setTestResult] = useState(null); // {ok, latency_ms, error}
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);
  const [savingKey, setSavingKey] = useState(false);
  const [cost, setCost] = useState(null);

  useEffect(() => {
    llmApi.getConfig().then((data) => {
      setConfig(data);
      setSelected(data.provider);
      setModel(data.model);
    }).catch(() => {});
  }, []);

  const checkFreq = agent?.check_frequency ?? 300;

  useEffect(() => {
    if (selected === 'ollama') { setCost(0); return; }
    llmApi.getCost(selected, model, checkFreq).then(d => setCost(d.cost)).catch(() => setCost(null));
  }, [selected, model, checkFreq]);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await llmApi.test();
      setTestResult(r);
    } catch (e) {
      setTestResult({ ok: false, latency_ms: 0, error: e.message });
    } finally {
      setTesting(false);
    }
  };

  const handleSaveKey = async () => {
    if (!openaiKey.trim()) return;
    setSavingKey(true);
    try {
      await llmApi.saveKey('openai_api_key', openaiKey.trim());
      setOpenaiKey('');
      setShowKey(false);
      const updated = await llmApi.getConfig();
      setConfig(updated);
    } catch (e) {
      setSaveMsg({ ok: false, text: e.message });
    } finally {
      setSavingKey(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      await llmApi.patchConfig({ provider: selected, model });
      setSaveMsg({ ok: true, text: 'Saved' });
      const updated = await llmApi.getConfig();
      setConfig(updated);
    } catch (e) {
      setSaveMsg({ ok: false, text: e.message });
    } finally {
      setSaving(false);
    }
  };


  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)', padding: 'var(--space-2) 0' }}>
      <div style={{ ...label }}>LLM MODEL</div>

      {PROVIDERS.map(({ id, label: pLabel, models }) => {
        const active = selected === id;
        return (
          <div
            key={id}
            style={{
              background: active ? 'var(--color-bg-elevated)' : 'transparent',
              border: `1px solid ${active ? 'var(--color-accent-primary)' : 'var(--color-border)'}`,
              borderRadius: 'var(--radius-sm)',
              padding: 'var(--space-4)',
              cursor: 'pointer',
            }}
            onClick={() => { setSelected(id); setModel(models[0]); }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: active ? 'var(--space-3)' : 0 }}>
              <span style={{ color: active ? 'var(--color-accent-primary)' : 'var(--color-text-muted)', ...mono }}>
                {active ? '●' : '○'}
              </span>
              <span style={{ ...mono, color: active ? 'var(--color-text-primary)' : 'var(--color-text-secondary)' }}>
                {pLabel}
              </span>
            </div>

            {active && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', paddingLeft: 'var(--space-5)' }}>
                {/* Model picker */}
                <div>
                  <div style={label}>MODEL</div>
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    style={{ ...inputStyle, width: 'auto', cursor: 'pointer' }}
                  >
                    {models.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>

                {/* Cost */}
                <div style={{ ...mono, fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  {id === 'ollama' ? 'Cost: Free' :
                    cost !== null ? `Est. cost: ~$${cost}/month` :
                    'Est. cost: unknown model'}
                </div>

                {/* Key status */}
                {id === 'claude' && (
                  <div style={{ ...mono, fontSize: 'var(--font-size-xs)', color: config?.has_claude_key ? 'var(--color-accent-primary)' : 'var(--color-accent-warning)' }}>
                    API Key: {config?.has_claude_key ? '✓ Connected via vault' : '✗ Not set (add anthropic_api_key to vault)'}
                  </div>
                )}

                {id === 'openai' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                    {config?.has_openai_key && !showKey ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                        <span style={{ ...mono, fontSize: 'var(--font-size-xs)', color: 'var(--color-accent-primary)' }}>✓ Key saved</span>
                        <button style={{ ...btn('var(--color-text-muted)'), padding: '2px 8px', fontSize: 'var(--font-size-xs)' }}
                          onClick={(e) => { e.stopPropagation(); setShowKey(true); }}>✏ Replace</button>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', gap: 'var(--space-2)' }} onClick={(e) => e.stopPropagation()}>
                        <input
                          type="password"
                          placeholder="sk-..."
                          value={openaiKey}
                          onChange={(e) => setOpenaiKey(e.target.value)}
                          style={{ ...inputStyle, flex: 1 }}
                        />
                        <button
                          disabled={savingKey || !openaiKey.trim()}
                          onClick={(e) => { e.stopPropagation(); handleSaveKey(); }}
                          style={{ ...btn('var(--color-accent-secondary)'), opacity: savingKey ? 0.6 : 1 }}
                        >
                          {savingKey ? '...' : 'SAVE KEY'}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center', flexWrap: 'wrap' }}>
        <button
          disabled={testing}
          onClick={handleTest}
          style={{ ...btn('var(--color-accent-secondary)'), opacity: testing ? 0.6 : 1 }}
        >
          {testing ? '⟳ TESTING...' : 'TEST LLM'}
        </button>
        <button
          disabled={saving}
          onClick={handleSave}
          style={{ ...btn('var(--color-accent-primary)'), opacity: saving ? 0.6 : 1 }}
        >
          {saving ? '...' : 'SAVE'}
        </button>
        {saveMsg && (
          <span style={{ ...mono, fontSize: 'var(--font-size-xs)', color: saveMsg.ok ? 'var(--color-accent-primary)' : 'var(--color-accent-danger)' }}>
            {saveMsg.ok ? '✓' : '✗'} {saveMsg.text}
          </span>
        )}
        {testResult && (
          <span style={{ ...mono, fontSize: 'var(--font-size-xs)', color: testResult.ok ? 'var(--color-accent-primary)' : 'var(--color-accent-danger)' }}>
            {testResult.ok ? `✓ OK (${testResult.latency_ms}ms)` : `✗ ${testResult.error ?? 'failed'}`}
          </span>
        )}
      </div>
    </div>
  );
}
