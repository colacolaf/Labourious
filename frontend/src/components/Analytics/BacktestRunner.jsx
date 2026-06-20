import React, { useState, useEffect } from 'react';
import useAnalyticsStore from '../../stores/analytics.store';
import EquityChart from './EquityChart';

const inputStyle = {
  background: 'var(--color-bg-tertiary)',
  border: '1px solid var(--color-border)',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
  padding: '6px 10px',
  borderRadius: 'var(--radius-sm)',
};

const labelStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-xs)',
  color: 'var(--color-text-muted)',
  letterSpacing: '0.08em',
  marginBottom: 4,
  display: 'block',
};

export default function BacktestRunner({ agents = [] }) {
  const { runBacktest, backtestStatus, backtestResult } = useAnalyticsStore();
  const [form, setForm] = useState({
    agent_id: agents[0]?.id ?? '',
    start_date: '2024-01-01',
    end_date: '2024-06-30',
    mode: 'basic',
  });

  useEffect(() => {
    if (!form.agent_id && agents.length > 0) {
      setForm((f) => ({ ...f, agent_id: agents[0].id }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agents]);

  const handleRun = () => {
    if (!form.agent_id) return;
    runBacktest({ ...form, agent_id: Number(form.agent_id) });
  };

  const equityData = backtestResult?.equity_curve ?? [];
  const stats = backtestResult ?? {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {/* Form */}
      <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <span style={labelStyle}>AGENT</span>
          <select
            style={{ ...inputStyle, cursor: 'pointer' }}
            value={form.agent_id}
            onChange={(e) => setForm({ ...form, agent_id: e.target.value })}
          >
            {agents.length === 0 && <option value="">No agents</option>}
            {agents.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        <div>
          <span style={labelStyle}>FROM</span>
          <input style={inputStyle} type="date" value={form.start_date}
            onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
        </div>
        <div>
          <span style={labelStyle}>TO</span>
          <input style={inputStyle} type="date" value={form.end_date}
            onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
        </div>
        <div>
          <span style={labelStyle}>MODE</span>
          <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
            {['basic', 'walk_forward'].map((m) => (
              <label key={m} style={{ ...labelStyle, marginBottom: 0, cursor: 'pointer', color: form.mode === m ? 'var(--color-text-primary)' : undefined }}>
                <input type="radio" name="mode" value={m} checked={form.mode === m}
                  onChange={() => setForm({ ...form, mode: m })}
                  style={{ marginRight: 4 }} />
                {m === 'basic' ? 'Basic' : 'Walk-Fwd'}
              </label>
            ))}
          </div>
        </div>
        <button
          onClick={handleRun}
          disabled={backtestStatus === 'running' || !form.agent_id}
          style={{
            ...inputStyle,
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-accent-primary)',
            color: 'var(--color-accent-primary)',
            cursor: backtestStatus === 'running' ? 'not-allowed' : 'pointer',
            letterSpacing: '0.08em',
            opacity: backtestStatus === 'running' ? 0.6 : 1,
          }}
        >
          {backtestStatus === 'running' ? '⟳ RUNNING...' : '▶ RUN BACKTEST'}
        </button>
      </div>

      {/* Results */}
      {backtestStatus === 'done' && stats && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-4)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-6)', flexWrap: 'wrap' }}>
            {[
              { label: 'RETURN', value: stats.total_return != null ? `${stats.total_return > 0 ? '+' : ''}${stats.total_return.toFixed(1)}%` : '—', color: (stats.total_return ?? 0) >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)' },
              { label: 'WIN RATE', value: stats.win_rate != null ? `${stats.win_rate.toFixed(1)}%` : '—', color: 'var(--color-text-primary)' },
              { label: 'SHARPE', value: stats.sharpe_ratio != null ? stats.sharpe_ratio.toFixed(2) : '—', color: 'var(--color-accent-secondary)' },
              { label: 'MAX DD', value: stats.max_drawdown != null ? `${(stats.max_drawdown * 100).toFixed(1)}%` : '—', color: 'var(--color-accent-warning)' },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <span style={{ ...labelStyle }}>{label}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-lg)', fontWeight: 700, color }}>{value}</span>
              </div>
            ))}
          </div>
          {equityData.length > 0 && <EquityChart data={equityData} height={160} />}
        </div>
      )}

      {backtestStatus === 'failed' && (
        <p style={{ color: 'var(--color-accent-danger)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
          Backtest failed: {backtestResult?.error ?? 'unknown error'}
        </p>
      )}
    </div>
  );
}
