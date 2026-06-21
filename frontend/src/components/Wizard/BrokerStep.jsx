import React, { useState } from 'react';
import useWizardStore from '../../stores/wizard.store';
import { brokersApi } from '../../utils/api-client';

const EXCHANGES = ['alpaca', 'binance', 'kraken', 'ibkr'];

export default function BrokerStep() {
  const { setFormData, nextStep } = useWizardStore((s) => ({
    setFormData: s.setFormData,
    nextStep: s.nextStep,
  }));
  const [exchange, setExchange] = useState('alpaca');
  const [apiKey, setApiKey] = useState('');
  const [secret, setSecret] = useState('');
  const [isPaper, setIsPaper] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleConnect() {
    setLoading(true);
    setError('');
    try {
      await brokersApi.connect({ exchange, api_key: apiKey, api_secret: secret, is_paper: isPaper });
      setFormData('broker', { exchange, isPaper });
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
          Connect a Broker
        </h2>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Add your first broker connection, or skip for now.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <label style={labelStyle}>
          Exchange
          <select value={exchange} onChange={(e) => setExchange(e.target.value)} style={inputStyle}>
            {EXCHANGES.map((ex) => (
              <option key={ex} value={ex}>{ex.toUpperCase()}</option>
            ))}
          </select>
        </label>

        <label style={labelStyle}>
          API Key
          <input
            type="text"
            value={apiKey}
            onChange={(e) => { setApiKey(e.target.value); setError(''); }}
            placeholder="Enter API key"
            style={inputStyle}
          />
        </label>

        <label style={labelStyle}>
          API Secret
          <input
            type="password"
            value={secret}
            onChange={(e) => { setSecret(e.target.value); setError(''); }}
            placeholder="Enter API secret"
            style={inputStyle}
          />
        </label>

        <label style={{ ...labelStyle, flexDirection: 'row', alignItems: 'center', gap: 'var(--space-3)', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={isPaper}
            onChange={(e) => setIsPaper(e.target.checked)}
            style={{ width: 16, height: 16, accentColor: 'var(--color-accent-primary)' }}
          />
          Paper trading mode
        </label>
      </div>

      {error && <p style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', fontFamily: 'var(--font-mono)' }}>{error}</p>}

      <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
        <button onClick={handleConnect} disabled={loading || !apiKey || !secret} style={btnPrimary}>
          {loading ? 'Connecting…' : 'Connect'}
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
