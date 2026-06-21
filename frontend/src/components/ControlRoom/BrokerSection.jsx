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
