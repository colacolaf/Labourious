import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useTradesStore } from '../stores/trades.store';
import useAgentsStore from '../stores/agents.store';
import { useWebSocketStore } from '../stores/websocket.store';

const card = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-primary)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4, 1rem)',
  fontFamily: 'var(--font-mono)',
};

const thStyle = {
  textAlign: 'left',
  padding: '0.5rem 0.75rem',
  borderBottom: '1px solid var(--border-primary)',
  color: 'var(--text-muted)',
  fontSize: '11px',
  fontWeight: 600,
  letterSpacing: '0.08em',
};

const tdStyle = {
  padding: '0.4rem 0.75rem',
  borderBottom: '1px solid var(--border-primary)',
  fontSize: '12px',
  color: 'var(--text-primary)',
};

const pnlStyle = (val) => ({
  ...tdStyle,
  color: (val ?? 0) >= 0 ? 'var(--accent-primary)' : 'var(--accent-danger)',
  fontWeight: 600,
});

const inputStyle = {
  background: 'var(--bg-tertiary)',
  border: '1px solid var(--border-primary)',
  borderRadius: 'var(--radius-sm)',
  padding: '0.35rem 0.6rem',
  color: 'var(--text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: '11px',
  minWidth: 60,
  outline: 'none',
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
  const lastMessage = useWebSocketStore((s) => s.lastMessage);

  const [symbol, setSymbol] = useState('');
  const [agentId, setAgentId] = useState('');
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchTrades({ limit: 100 });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Refetch on filter change
  useEffect(() => {
    fetchTrades({ limit: 100, symbol: symbol || undefined, agent_id: agentId || undefined, status: status || undefined });
  }, [symbol, agentId, status]); // eslint-disable-line react-hooks/exhaustive-deps

  // WebSocket live update: refetch on trade events
  useEffect(() => {
    if (!lastMessage) return;
    const ev = lastMessage.event ?? lastMessage.type;
    if (['trade_executed', 'live_order_filled', 'trade_update'].includes(ev)) {
      fetchTrades({ limit: 100, symbol: symbol || undefined, agent_id: agentId || undefined, status: status || undefined });
    }
  }, [lastMessage]); // eslint-disable-line react-hooks/exhaustive-deps

  const symbols = useMemo(() => [...new Set(trades.map((t) => t.symbol).filter(Boolean))].sort(), [trades]);

  const agentMap = useMemo(() => {
    const m = {};
    agents.forEach((a) => { m[a.id] = a.name ?? `Agent #${a.id}`; });
    return m;
  }, [agents]);

  // Client-side search filter
  const filtered = useMemo(() => {
    if (!search.trim()) return trades;
    const q = search.toLowerCase();
    return trades.filter(t =>
      (t.symbol ?? '').toLowerCase().includes(q) ||
      (t.side ?? '').toLowerCase().includes(q) ||
      String(t.id).includes(q) ||
      (agentMap[t.agent_id] ?? '').toLowerCase().includes(q)
    );
  }, [trades, search, agentMap]);

  const totalPnl = filtered.reduce((s, t) => s + (t.pnl ?? 0), 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      style={{ fontFamily: 'var(--font-mono)', height: '100%', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ color: 'var(--accent-primary)', fontSize: '18px', fontFamily: 'var(--font-sans)', margin: 0 }}>
          Trade History
        </h1>
        <span style={{ fontSize: '16px', color: totalPnl >= 0 ? 'var(--accent-primary)' : 'var(--accent-danger)', fontWeight: 700 }}>
          {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)}
        </span>
      </div>

      {error && <div style={{ color: 'var(--accent-danger)', fontSize: '11px' }}>{error}</div>}

      <div style={{ ...card, display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <label style={{ color: 'var(--text-muted)', fontSize: '11px', letterSpacing: '0.08em' }}>FILTERS</label>
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
        <input
          type="text"
          placeholder="Search symbol, side, agent…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ ...inputStyle, minWidth: 180, flex: 1 }}
        />
      </div>

      <div style={{ ...card, padding: 0, overflow: 'auto' }}>
        {loading && trades.length === 0 ? (
          <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} style={{ height: 32, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', opacity: 0.5, animation: 'pulse 1.5s infinite' }} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)', textAlign: 'center' }}>No trades found.</div>
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
              {filtered.map((t) => (
                <tr key={t.id} style={{ transition: 'background 0.15s' }}>
                  <td style={tdStyle}>{fmtDate(t.opened_at)}</td>
                  <td style={tdStyle}>{agentMap[t.agent_id] ?? `#${t.agent_id}`}</td>
                  <td style={tdStyle}>{t.symbol}</td>
                  <td style={{ ...tdStyle, color: t.side?.toLowerCase() === 'buy' ? 'var(--accent-primary)' : 'var(--accent-danger)' }}>{t.side}</td>
                  <td style={{ ...tdStyle, color: t.status === 'open' ? 'var(--accent-secondary)' : t.status === 'cancelled' ? 'var(--text-muted)' : 'var(--text-primary)' }}>{t.status}</td>
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