import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { vaultApi } from '../utils/api-client';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const inputStyle = {
  background: 'var(--color-bg-tertiary)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-sm)',
  padding: '0.5rem 0.75rem',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
  width: '100%',
};

const labelStyle = {
  fontSize: 'var(--font-size-xs)',
  color: 'var(--color-text-muted)',
  letterSpacing: '0.08em',
  display: 'block',
  marginBottom: 'var(--space-1)',
};

const btnStyle = {
  padding: '0.5rem 1.25rem',
  background: 'var(--color-accent-primary)',
  color: 'var(--color-text-inverse)',
  border: 'none',
  borderRadius: 'var(--radius-sm)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
  fontWeight: 600,
  cursor: 'pointer',
};

const btnDanger = {
  ...btnStyle,
  background: 'var(--color-accent-danger)',
};

const EXCHANGES = ['alpaca', 'binance', 'kraken'];

export default function VaultSettings() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [testResults, setTestResults] = useState({});

  // New key form
  const [newExchange, setNewExchange] = useState('alpaca');
  const [newApiKey, setNewApiKey] = useState('');
  const [newApiSecret, setNewApiSecret] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchKeys = useCallback(async () => {
    try {
      setLoading(true);
      const data = await vaultApi.listKeys();
      setKeys(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchKeys(); }, [fetchKeys]);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!newApiKey.trim() || !newApiSecret.trim()) return;
    setSaving(true);
    try {
      await vaultApi.setKey({ exchange: newExchange, api_key: newApiKey, api_secret: newApiSecret });
      setNewApiKey('');
      setNewApiSecret('');
      await fetchKeys();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (exchange) => {
    try {
      await vaultApi.deleteKey(exchange);
      setTestResults((prev) => { const next = { ...prev }; delete next[exchange]; return next; });
      await fetchKeys();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleTest = async (exchange) => {
    try {
      setTestResults((prev) => ({ ...prev, [exchange]: 'testing' }));
      const res = await vaultApi.testConnection(exchange);
      setTestResults((prev) => ({ ...prev, [exchange]: res?.ok ?? res?.status === 'ok' ? 'ok' : 'fail' }));
    } catch {
      setTestResults((prev) => ({ ...prev, [exchange]: 'fail' }));
    }
  };

  const storedExchanges = new Set(keys.map((k) => k.exchange ?? k.key));

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      style={{ fontFamily: 'var(--font-mono)', padding: 'var(--space-6)', maxWidth: 720, height: '100%', overflow: 'auto' }}
    >
      <h1 style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-2xl)', fontFamily: 'var(--font-sans)', marginBottom: 'var(--space-6)' }}>
        Encrypted Vault
      </h1>

      {error && <div style={{ color: 'var(--color-text-danger)', fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-3)' }}>{error}</div>}

      {/* Stored keys */}
      <div style={{ ...card, marginBottom: 'var(--space-4)' }}>
        <h2 style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', letterSpacing: '0.08em', marginBottom: 'var(--space-3)' }}>
          STORED CREDENTIALS
        </h2>
        {loading ? (
          <div style={{ color: 'var(--color-text-muted)' }}>Loading...</div>
        ) : storedExchanges.size === 0 ? (
          <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No credentials stored.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {[...storedExchanges].map((ex) => {
              const status = testResults[ex];
              return (
                <div key={ex} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
                  <span style={{ color: 'var(--color-text-primary)', textTransform: 'uppercase', fontSize: 'var(--font-size-sm)' }}>{ex}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    {status === 'testing' && <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>testing...</span>}
                    {status === 'ok' && <span style={{ color: 'var(--color-accent-success)', fontSize: 'var(--font-size-xs)' }}>✓ connected</span>}
                    {status === 'fail' && <span style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-xs)' }}>✗ failed</span>}
                    <button onClick={() => handleTest(ex)} style={{ ...btnStyle, padding: '0.25rem 0.75rem', fontSize: 'var(--font-size-xs)', background: 'var(--color-bg-tertiary)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)' }}>Test</button>
                    <button onClick={() => handleDelete(ex)} style={{ ...btnDanger, padding: '0.25rem 0.75rem', fontSize: 'var(--font-size-xs)' }}>Delete</button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add new key */}
      <div style={card}>
        <h2 style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', letterSpacing: '0.08em', marginBottom: 'var(--space-3)' }}>
          ADD CREDENTIALS
        </h2>
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div>
            <label style={labelStyle}>EXCHANGE</label>
            <select value={newExchange} onChange={(e) => setNewExchange(e.target.value)} style={inputStyle}>
              {EXCHANGES.map((ex) => <option key={ex} value={ex}>{ex.toUpperCase()}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>API KEY</label>
            <input style={inputStyle} value={newApiKey} onChange={(e) => setNewApiKey(e.target.value)} placeholder="Enter API key" />
          </div>
          <div>
            <label style={labelStyle}>API SECRET</label>
            <input style={inputStyle} type="password" value={newApiSecret} onChange={(e) => setNewApiSecret(e.target.value)} placeholder="Enter API secret" />
          </div>
          <div>
            <button type="submit" disabled={saving || !newApiKey.trim() || !newApiSecret.trim()} style={{ ...btnStyle, opacity: saving || !newApiKey.trim() || !newApiSecret.trim() ? 0.5 : 1 }}>
              {saving ? 'ENCRYPTING...' : 'STORE CREDENTIALS'}
            </button>
          </div>
        </form>
      </div>
    </motion.div>
  );
}