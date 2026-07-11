import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useTradesStore } from '../stores/trades.store';
import useAgentsStore from '../stores/agents.store';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const thStyle = {
  textAlign: 'left',
  padding: '0.5rem 0.75rem',
  borderBottom: '1px solid var(--color-border)',
  color: 'var(--color-text-muted)',
  fontSize: 'var(--font-size-xs)',
  fontWeight: 600,
  letterSpacing: '0.08em',
};

const tdStyle = {
  padding: '0.4rem 0.75rem',
  borderBottom: '1px solid var(--color-border-subtle)',
  fontSize: 'var(--font-size-sm)',
  color: 'var(--color-text-primary)',
};

const pnlStyle = (val) => ({
  ...tdStyle,
  color: (val ?? 0) >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)',
  fontWeight: 600,
});

const inputStyle = {
  background: 'var(--color-bg-tertiary)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-sm)',
  padding: '0.35rem 0.6rem',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-xs)',
  minWidth: 60,
};

const selectStyle = {
  ...inputStyle,
  minWidth: 140,
};

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function Trades() {
  const { trades, loading, error, fetchTrades } = useTradesStore();
  const agents = useAgentsStore((s) => s.agents);
  const [symbol, setSymbol] = useState('');
  const [agentId, setAgentId] = useState('');
  const [status, setStatus] = useState('');

  useEffect(() => {
    fetchTrades({ limit: 100 });
  }, [fetchTrades]);

  useEffect(() => {
    fetchTrades({ limit: 100, symbol: symbol || undefined, agent_id: agentId || undefined, status: status || undefined });
  }, [symbol, agentId, status, fetchTrades]);

  const symbols = useMemo(() => [...new Set(trades.map((t) => t.symbol).filter(Boolean))].sort(), [trades]);

  const agentMap = useMemo(() => {
    const m = {};
    agents.forEach((a) => { m[a.id] = a.name ?? `Agent #${a.id}`; });
    return m;
  }, [agents]);

  const totalPnl = trades.reduce((s, t) => s + (t.pnl ?? 0), 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      style={{ fontFamily: 'var(--font-mono)', padding: 'var(--space-6)', height: '100%', overflow: 'auto' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
        <h1 style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-2xl)', fontFamily: 'var(--font-sans)' }}>
          Trade History
        </h1>
        <span style={{ fontSize: 'var(--font-size-lg)', color: totalPnl >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)', fontWeight: 700 }}>
          {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)}
        </span>
      </div>

      {error && <div style={{ color: 'var(--color-text-danger)', fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-3)' }}>{error}</div>}

      <div style={{ ...card, display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-4)', flexWrap: 'wrap', alignItems: 'center' }}>
        <label style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)', letterSpacing: '0.08em' }}>
          FILTERS
        </label>
        <select style={selectStyle} value={agentId} onChange={(e) => setAgentId(e.target.value)}>
          <option value="">All Agents</option>
          {Object.entries(agentMap).map(([id, name]) => (
            <option key={id} value={id}>{name}</option>
          ))}
        </select>
        <select style={selectStyle} value={symbol} onChange={(e) => setSymbol(e.target.value)}>
          <option value="">All Symbols</option>
          {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select style={selectStyle} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="closed">Closed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      <div style={{ ...card, padding: 0, overflow: 'auto' }}>
        {loading && trades.length === 0 ? (
          <div style={{ padding: 'var(--space-4)', color: 'var(--color-text-muted)', textAlign: 'center' }}>Loading...</div>
        ) : trades.length === 0 ? (
          <div style={{ padding: 'var(--space-4)', color: 'var(--color-text-muted)', textAlign: 'center' }}>No trades yet.</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={thStyle}>TIME</th>
                <th style={thStyle}>AGENT</th>
                <th style={thStyle}>SYMBOL</th>
                <th style={thStyle}>SIDE</th>
                <th style={thStyle}>STATUS</th>
                <th style={thStyle}>QTY</th>
                <th style={thStyle}>ENTRY</th>
                <th style={thStyle}>EXIT</th>
                <th style={thStyle}>PNL</th>
                <th style={thStyle}>PNL %</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => (
                <tr key={t.id} style={{ transition: 'background var(--transition-fast)' }}>
                  <td style={tdStyle}>{fmtDate(t.opened_at)}</td>
                  <td style={tdStyle}>{agentMap[t.agent_id] ?? `#${t.agent_id}`}</td>
                  <td style={tdStyle}>{t.symbol}</td>
                  <td style={{ ...tdStyle, color: t.side?.toLowerCase() === 'buy' ? 'var(--color-accent-success)' : 'var(--color-accent-danger)' }}>{t.side}</td>
                  <td style={{ ...tdStyle, color: t.status === 'open' ? 'var(--color-agent-running)' : t.status === 'cancelled' ? 'var(--color-text-muted)' : 'var(--color-text-primary)' }}>{t.status}</td>
                  <td style={tdStyle}>{t.quantity}</td>
                  <td style={tdStyle}>{t.entry_price?.toFixed(2) ?? '—'}</td>
                  <td style={tdStyle}>{t.exit_price?.toFixed(2) ?? '—'}</td>
                  <td style={pnlStyle(t.pnl)}>{t.pnl != null ? `${t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)}` : '—'}</td>
                  <td style={pnlStyle(t.pnl_pct)}>{t.pnl_pct != null ? `${t.pnl_pct >= 0 ? '+' : ''}${t.pnl_pct.toFixed(2)}%` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </motion.div>
  );
}