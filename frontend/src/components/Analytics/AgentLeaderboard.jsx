import React from 'react';

const COL_LABELS = {
  return: 'P&L',
  sharpe: 'Sharpe',
  win_rate: 'Win %',
  trades: 'Trades',
};

const BAR_MAX_WIDTH = 80; // px

function InlineBar({ value, max, color }) {
  const width = max > 0 ? Math.max(2, (Math.abs(value) / max) * BAR_MAX_WIDTH) : 2;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{
        width: BAR_MAX_WIDTH,
        height: 6,
        background: 'var(--color-bg-elevated)',
        borderRadius: 3,
        overflow: 'hidden',
      }}>
        <div style={{ width, height: '100%', background: color, borderRadius: 3 }} />
      </div>
    </div>
  );
}

export default function AgentLeaderboard({ rows = [], sortBy = 'return', onSort }) {
  const maxPnl = Math.max(...rows.map((r) => Math.abs(r.total_pnl)), 1);

  const col = (key, label) => (
    <th
      onClick={() => onSort?.(key)}
      style={{
        padding: '6px 12px',
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--font-size-xs)',
        color: sortBy === key ? 'var(--color-accent-primary)' : 'var(--color-text-muted)',
        letterSpacing: '0.08em',
        cursor: 'pointer',
        userSelect: 'none',
        textAlign: 'left',
        borderBottom: '1px solid var(--color-border)',
        whiteSpace: 'nowrap',
      }}
    >
      {label} {sortBy === key ? '▼' : ''}
    </th>
  );

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr>
          {col('return', 'AGENT')}
          {col('return', 'P&L')}
          <th style={{ padding: '6px 12px', borderBottom: '1px solid var(--color-border)' }} />
          {col('win_rate', 'WIN %')}
          {col('sharpe', 'SHARPE')}
          {col('trades', 'TRADES')}
          <th style={{ padding: '6px 12px', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', letterSpacing: '0.08em', borderBottom: '1px solid var(--color-border)', fontFamily: 'var(--font-mono)' }}>CONF</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => {
          const pnlColor = row.total_pnl >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)';
          return (
            <tr
              key={row.id}
              style={{
                background: i % 2 === 0 ? 'transparent' : 'var(--color-bg-card)',
                transition: 'background var(--transition-fast)',
              }}
            >
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>
                {row.name}
                <span style={{ marginLeft: 6, fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  {row.room?.replace('_', ' ')}
                </span>
              </td>
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: pnlColor, fontWeight: 700, whiteSpace: 'nowrap' }}>
                {row.total_pnl >= 0 ? '+' : ''}{row.total_pnl.toFixed(2)}
              </td>
              <td style={{ padding: '7px 12px' }}>
                <InlineBar value={row.total_pnl} max={maxPnl} color={pnlColor} />
              </td>
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                {row.win_rate.toFixed(1)}%
              </td>
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: row.sharpe_ratio != null ? 'var(--color-accent-secondary)' : 'var(--color-text-muted)' }}>
                {row.sharpe_ratio != null ? row.sharpe_ratio.toFixed(2) : '—'}
              </td>
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                {row.total_trades}
              </td>
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                {row.confidence_score}%
              </td>
            </tr>
          );
        })}
        {rows.length === 0 && (
          <tr>
            <td colSpan={7} style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
              No agents yet
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
