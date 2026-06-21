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
