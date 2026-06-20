import React from 'react';

const HIGH_CORR_THRESHOLD = 0.7;

export default function CorrelationMatrix({ data = {} }) {
  const agents = Object.keys(data);
  // Collect all unique agent names (including those only appearing as values)
  const allNames = new Set(agents);
  agents.forEach((a) => Object.keys(data[a] || {}).forEach((b) => allNames.add(b)));
  const names = Array.from(allNames).sort();

  if (names.length === 0) {
    return (
      <p style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
        Insufficient data — need 30+ days of snapshots
      </p>
    );
  }

  const cell = (a, b) => {
    if (a === b) return { value: null, high: false };
    const v = data[a]?.[b] ?? data[b]?.[a] ?? null;
    return { value: v, high: v != null && Math.abs(v) >= HIGH_CORR_THRESHOLD };
  };

  const tdBase = {
    padding: '6px 14px',
    fontFamily: 'var(--font-mono)',
    fontSize: 'var(--font-size-xs)',
    borderBottom: '1px solid var(--color-border-subtle)',
    textAlign: 'center',
    whiteSpace: 'nowrap',
  };

  return (
    <div style={{ overflowX: 'auto' }}>
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: 8 }}>
        LAST 30D DAILY RETURNS &nbsp;
        <span style={{ color: 'var(--color-accent-warning)' }}>⚠ = corr &gt; 0.7</span>
      </p>
      <table style={{ borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ ...tdBase, color: 'var(--color-text-muted)', textAlign: 'left' }} />
            {names.map((n) => (
              <th key={n} style={{ ...tdBase, color: 'var(--color-accent-secondary)' }}>{n}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {names.map((a, i) => (
            <tr key={a} style={{ background: i % 2 === 0 ? 'transparent' : 'var(--color-bg-card)' }}>
              <td style={{ ...tdBase, color: 'var(--color-accent-secondary)', textAlign: 'left', paddingLeft: 0 }}>{a}</td>
              {names.map((b) => {
                const { value, high } = cell(a, b);
                if (value === null) {
                  return (
                    <td key={b} style={{ ...tdBase, color: 'var(--color-text-muted)' }}>—</td>
                  );
                }
                return (
                  <td
                    key={b}
                    style={{
                      ...tdBase,
                      color: high ? 'var(--color-accent-warning)' : 'var(--color-text-primary)',
                    }}
                  >
                    {high && '⚠ '}{value.toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
