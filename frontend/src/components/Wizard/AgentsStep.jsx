import React, { useState } from 'react';
import useWizardStore from '../../stores/wizard.store';
import { agentsApi } from '../../utils/api-client';

const TEMPLATES = [
  { id: 'momentum_scalper', name: 'Momentum Scalper', strategy_type: 'momentum', risk_level: 'High', strategy_config: { strategy: 'momentum_scalp' } },
  { id: 'mean_reversion', name: 'Mean Reversion', strategy_type: 'mean_reversion', risk_level: 'Medium', strategy_config: { strategy: 'mean_reversion' } },
  { id: 'trend_follower', name: 'Trend Follower', strategy_type: 'trend', risk_level: 'Low', strategy_config: { strategy: 'trend_follow' } },
  { id: 'arbitrage_bot', name: 'Arbitrage Bot', strategy_type: 'arbitrage', risk_level: 'Medium', strategy_config: { strategy: 'arbitrage' } },
];

const RISK_COLORS = {
  High: 'var(--color-accent-danger)',
  Medium: 'var(--color-accent-warning)',
  Low: 'var(--color-accent-primary)',
};

export default function AgentsStep() {
  const { submitWizard } = useWizardStore((s) => ({ submitWizard: s.submitWizard }));
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function toggle(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function handleHire() {
    setLoading(true);
    setError('');
    try {
      const toHire = TEMPLATES.filter((t) => selected.has(t.id));
      await Promise.all(
        toHire.map((t) =>
          agentsApi.create({
            name: t.name,
            strategy_type: t.strategy_type,
            strategy_config: t.strategy_config,
            risk_config: {},
          })
        )
      );
      submitWizard();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleSkip() {
    submitWizard();
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div>
        <h2 style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', marginBottom: 'var(--space-2)' }}>
          Hire Agents
        </h2>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Select prebuilt agent templates to deploy.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
        {TEMPLATES.map((t) => {
          const isSelected = selected.has(t.id);
          return (
            <div
              key={t.id}
              onClick={() => toggle(t.id)}
              style={{
                padding: 'var(--space-4)',
                background: isSelected ? 'var(--color-bg-elevated)' : 'var(--color-bg-card)',
                border: `1px solid ${isSelected ? 'var(--color-accent-primary)' : 'var(--color-border)'}`,
                borderRadius: 'var(--radius-lg)',
                cursor: 'pointer',
                transition: 'var(--transition-fast)',
                boxShadow: isSelected ? 'var(--shadow-glow-green)' : 'none',
              }}
            >
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 'var(--space-2)' }}>
                {t.name}
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-2)' }}>
                {t.strategy_type}
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: RISK_COLORS[t.risk_level], fontFamily: 'var(--font-mono)' }}>
                Risk: {t.risk_level}
              </div>
            </div>
          );
        })}
      </div>

      {error && <p style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', fontFamily: 'var(--font-mono)' }}>{error}</p>}

      <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
        <button
          onClick={handleHire}
          disabled={loading || selected.size === 0}
          style={{
            padding: 'var(--space-3) var(--space-6)',
            background: selected.size > 0 ? 'var(--color-accent-primary)' : 'var(--color-border)',
            color: selected.size > 0 ? 'var(--color-bg-primary)' : 'var(--color-text-muted)',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            cursor: selected.size > 0 ? 'pointer' : 'not-allowed',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          {loading ? 'Hiring…' : `Hire Selected (${selected.size})`}
        </button>
        <button onClick={handleSkip} style={btnSecondary}>Skip</button>
      </div>
    </div>
  );
}

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
