import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ReferenceLine,
} from 'recharts';

export default function AttributionWaterfall({ data = null }) {
  if (!data || !data.contributions || Object.keys(data.contributions).length === 0) {
    return (
      <p style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
        No trades closed on this date
      </p>
    );
  }

  const entries = Object.entries(data.contributions)
    .sort((a, b) => b[1] - a[1]);

  const chartData = entries.map(([name, pct]) => ({ name, pct }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const val = payload[0].value;
    return (
      <div style={{
        background: 'var(--color-bg-elevated)',
        border: '1px solid var(--color-border-bright)',
        padding: '8px 12px',
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--font-size-xs)',
      }}>
        <div style={{ color: 'var(--color-text-secondary)', marginBottom: 2 }}>{label}</div>
        <div style={{ color: val >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)', fontWeight: 700 }}>
          {val >= 0 ? '+' : ''}{val.toFixed(1)}%
        </div>
      </div>
    );
  };

  return (
    <div>
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: 8 }}>
        P&L ATTRIBUTION — {data.date}
      </p>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 24, left: 8 }}>
          <XAxis
            dataKey="name"
            tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--color-text-muted)' }}
            tickLine={false}
            axisLine={{ stroke: 'var(--color-border)' }}
          />
          <YAxis
            tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(0)}%`}
            tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--color-text-muted)' }}
            tickLine={false}
            axisLine={false}
            width={48}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="var(--color-border-bright)" />
          <Bar dataKey="pct" radius={[2, 2, 0, 0]}>
            {chartData.map((entry) => (
              <Cell
                key={entry.name}
                fill={entry.pct >= 0 ? 'var(--color-accent-primary)' : 'var(--color-accent-danger)'}
                opacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
