import React, { useState } from 'react';
import useWizardStore from '../../stores/wizard.store';
import { agentsApi } from '../../utils/api-client';

const TEMPLATES = [
  { id: 'momentum_scalper', name: 'Momentum Scalper', strategy_type: 'momentum', risk_level: 'High', strategy_config: { strategy: 'momentum_scalp' } },
  { id: 'mean_reversion', name: 'Mean Reversion', strategy_type: 'mean_reversion', risk_level: 'Medium', strategy_config: { strategy: 'mean_reversion' } },
  { id: 'trend_follower', name: 'Trend Follower', strategy_type: 'trend', risk_level: 'Low', strategy_config: { strategy: 'trend_follow' } },
  { id: 'arbitrage_bot', name: 'Arbitrage Bot', strategy_type: 'arbitrage', risk_level: 'Medium', strategy_config: { strategy: 'arbitrage' } },
];

const TRADING_MODES = [
  {
    id: 'paper_only',
    label: 'Paper Trading Only',
    desc: 'Safest — simulated trades, no real money',
    is_paper_trading: true,
    execution_mode: 'autonomous',
  },
  {
    id: 'human_in_loop',
    label: 'Human Approval Required',
    desc: 'Every live trade waits for your approval',
    is_paper_trading: false,
    execution_mode: 'human_in_loop',
  },
  {
    id: 'risk_based',
    label: 'Semi-Autonomous',
    desc: 'Small/confident trades auto-execute; risky ones ask',
    is_paper_trading: false,
    execution_mode: 'risk_based',
  },
  {
    id: 'autonomous',
    label: 'Fully Autonomous',
    desc: 'All trades execute without asking — advanced users only',
    is_paper_trading: false,
    execution_mode: 'autonomous',
  },
];

const RISK_COLORS = {
  High: 'var(--color-accent-danger)',
  Medium: 'var(--color-accent-warning)',
  Low: 'var(--color-accent-primary)',
};

export default function AgentsStep() {
  const submitWizard = useWizardStore((s) => s.submitWizard);
  const [selected, setSelected] = useState(new Set());
  const [modeId, setModeId] = useState('paper_only'); // safe default
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
    const mode = TRADING_MODES.find((m) => m.id === modeId);
    const toHire = TEMPLATES.filter((t) => selected.has(t.id));
    const results = await Promise.allSettled(
      toHire.map((t) =>
        agentsApi.create({
          name: t.name,
          strategy_type: t.strategy_type,
          strategy_config: t.strategy_config,
          risk_config: {},
          is_paper_trading: mode.is_paper_trading,
          execution_mode: mode.execution_mode,
        })
      )
    );
    const failed = results.filter((r) => r.status === 'rejected');
    if (failed.length > 0) {
      setError(`${failed.length} agent(s) failed to create — you can add them from Control Room`);
    }
    setLoading(false);
    submitWizard();
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
          Select agents to deploy, then choose how they trade.
        </p>
      </div>

      {/* Agent template picker */}
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

      {/* Trading mode picker */}
      {selected.size > 0 && (
        <div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em', marginBottom: 'var(--space-3)' }}>
            HOW SHOULD THESE AGENTS TRADE?
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {TRADING_MODES.map((m) => {
              const active = modeId === m.id;
              return (
                <label
                  key={m.id}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 'var(--space-3)',
                    padding: 'var(--space-3) var(--space-4)',
                    background: active ? 'var(--color-bg-elevated)' : 'var(--color-bg-card)',
                    border: `1px solid ${active ? 'var(--color-accent-primary)' : 'var(--color-border)'}`,
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    transition: 'var(--transition-fast)',
                  }}
                >
                  <input
                    type="radio"
                    name="trading_mode"
                    value={m.id}
                    checked={active}
                    onChange={() => setModeId(m.id)}
                    style={{ marginTop: 3, accentColor: 'var(--color-accent-primary)' }}
                  />
                  <div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)', fontWeight: active ? 700 : 400 }}>
                      {m.label}
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 2 }}>
                      {m.desc}
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      )}

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
