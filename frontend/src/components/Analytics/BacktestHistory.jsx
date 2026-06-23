import { useEffect } from 'react';
import useAnalyticsStore from '../../stores/analytics.store';

const STATUS_COLOR = {
  done: 'var(--color-pnl-positive)',
  failed: 'var(--color-accent-danger, #ff4444)',
  running: 'var(--color-accent-warning, #ffb020)',
};

export default function BacktestHistory({ agentId = null }) {
  const { backtestHistory, fetchBacktestHistory, runBacktest } = useAnalyticsStore();

  useEffect(() => {
    fetchBacktestHistory(agentId);
  }, [agentId, fetchBacktestHistory]);

  if (!backtestHistory.length) return (
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-4)' }}>
      No backtest history.
    </div>
  );

  return (
    <div style={{ marginTop: 'var(--space-4)' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', letterSpacing: '0.08em', marginBottom: 'var(--space-3)' }}>
        RECENT RUNS
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>
        <thead>
          <tr style={{ color: 'var(--color-text-muted)', borderBottom: '1px solid var(--color-border)' }}>
            {['Agent', 'Period', 'Mode', 'Status', 'Run At', ''].map((h) => (
              <th key={h} style={{ textAlign: 'left', padding: '0.3rem 0.5rem', fontWeight: 'normal' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {backtestHistory.map((r) => (
            <tr key={r.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
              <td style={{ padding: '0.35rem 0.5rem' }}>#{r.agent_id ?? '—'}</td>
              <td style={{ padding: '0.35rem 0.5rem', color: 'var(--color-text-muted)' }}>
                {r.start_date} → {r.end_date}
              </td>
              <td style={{ padding: '0.35rem 0.5rem' }}>{r.mode}</td>
              <td style={{ padding: '0.35rem 0.5rem', color: STATUS_COLOR[r.status] ?? 'inherit' }}>
                {r.status.toUpperCase()}
              </td>
              <td style={{ padding: '0.35rem 0.5rem', color: 'var(--color-text-muted)' }}>
                {r.run_at?.slice(0, 16).replace('T', ' ')}
              </td>
              <td style={{ padding: '0.35rem 0.5rem' }}>
                <button
                  onClick={() => runBacktest({ agent_id: r.agent_id, start_date: r.start_date, end_date: r.end_date, mode: r.mode })}
                  style={{ background: 'none', border: '1px solid var(--color-border)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', cursor: 'pointer', padding: '0.15rem 0.4rem', borderRadius: 2 }}
                >
                  re-run
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
