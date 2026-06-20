import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';

const fmt = (val) =>
  val >= 0 ? `+$${val.toFixed(0)}` : `-$${Math.abs(val).toFixed(0)}`;

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
      <div style={{ color: 'var(--color-text-secondary)', marginBottom: 4 }}>{label}</div>
      <div style={{ color: val >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)', fontWeight: 700 }}>
        {fmt(val)}
      </div>
    </div>
  );
};

export default function EquityChart({ data = [], height = 200 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
        <CartesianGrid
          strokeDasharray="2 4"
          stroke="var(--color-border-subtle)"
          vertical={false}
        />
        <XAxis
          dataKey="date"
          tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={{ stroke: 'var(--color-border)' }}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={fmt}
          tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={false}
          width={64}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="var(--color-border-bright)" strokeDasharray="4 4" />
        <Line
          type="monotone"
          dataKey="pnl"
          stroke="var(--color-accent-secondary)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: 'var(--color-accent-secondary)', stroke: 'var(--color-bg-primary)' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
