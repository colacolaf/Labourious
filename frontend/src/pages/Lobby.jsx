import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { analyticsApi, agentsApi } from '../utils/api-client';
import { useWebSocketStore } from '../stores/websocket.store';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const rooms = [
  { key: 'long_term',     label: 'The Bloomberg',  path: '/warroom/long',  icon: '◈', accent: '#4a7eba' },
  { key: 'swing_trading', label: 'The Oak Office', path: '/warroom/swing', icon: '◎', accent: '#CC8833' },
  { key: 'day_trading',   label: 'The Pit',        path: '/warroom/day',   icon: '◉', accent: '#FF3333' },
];

function RoomScorecard({ room, agents, onEnter }) {
  const roomAgents = agents.filter(a => a.room === room.key);
  const running = roomAgents.filter(a => a.status === 'running').length;
  const totalPnl = roomAgents.reduce((s, a) => s + (a.total_pnl ?? 0), 0);
  const pnlColor = totalPnl >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)';

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onEnter(room.path)}
      style={{ ...card, border: `1px solid ${room.accent}44`, cursor: 'pointer', minWidth: 200, flex: 1 }}
    >
      <div style={{ color: room.accent, fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-2)' }}>
        {room.icon} {room.label}
      </div>
      <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>
        {running}/{roomAgents.length} agents running
      </div>
      <div style={{ fontSize: 'var(--font-size-lg)', color: pnlColor, fontWeight: 700 }}>
        {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)}
      </div>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
        TOTAL P&L
      </div>
    </motion.div>
  );
}

function AgentPanel({ label, agents, accent }) {
  const maxDD = agents.length > 0
    ? Math.max(...agents.map(a => Math.abs(a.max_drawdown ?? 0))).toFixed(1)
    : '0.0';
  return (
    <div style={{ ...card, border: `1px solid ${accent}44`, minWidth: 180 }}>
      <div style={{ color: accent, fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-2)', letterSpacing: '0.08em' }}>
        {label}
      </div>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
        Monitoring {agents.length} agents
      </div>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
        Max drawdown: <span style={{ color: 'var(--color-accent-warning)' }}>{maxDD}%</span>
      </div>
    </div>
  );
}

export default function Lobby() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState([]);
  const [portfolio, setPortfolio] = useState(null);
  const lastMessage = useWebSocketStore(s => s.lastMessage);

  useEffect(() => {
    Promise.all([
      agentsApi.list().catch(() => []),
      analyticsApi.portfolio().catch(() => null),
    ]).then(([agentList, portfolioData]) => {
      setAgents(agentList);
      setPortfolio(portfolioData);
    });
  }, []);

  useEffect(() => {
    if (!lastMessage) return;
    const reactive = ['trade_executed', 'live_order_filled', 'agent_update', 'agent_paused', 'portfolio_update'];
    if (reactive.includes(lastMessage.event ?? lastMessage.type)) {
      Promise.all([
        agentsApi.list().catch(() => []),
        analyticsApi.portfolio().catch(() => null),
      ]).then(([agentList, portfolioData]) => {
        setAgents(agentList);
        setPortfolio(portfolioData);
      });
    }
  }, [lastMessage]);

  const totalPnl = portfolio?.total_pnl ?? 0;
  const pnlColor = totalPnl >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      style={{ fontFamily: 'var(--font-mono)', padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-2xl)', letterSpacing: '0.1em' }}>
          ⬡ TRADING WARROOM
        </h1>
        <div style={{ textAlign: 'right' }}>
          <div style={{ color: pnlColor, fontSize: 'var(--font-size-xl)', fontWeight: 700 }}>
            {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)}
          </div>
          <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>PORTFOLIO P&L</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <AgentPanel label="◈ RISK AGENT" agents={agents} accent="var(--color-accent-primary)" />
        <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', flex: 1 }}>
          {rooms.map(r => (
            <RoomScorecard key={r.key} room={r} agents={agents} onEnter={navigate} />
          ))}
        </div>
        <AgentPanel label="⬡ BODYGUARD" agents={agents} accent="var(--color-accent-secondary)" />
      </div>

      <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
        {[
          { label: 'ACTIVE AGENTS', value: portfolio?.agent_count ?? agents.filter(a => a.status === 'running').length },
          { label: 'TOTAL TRADES',  value: portfolio?.total_trades ?? 0 },
          { label: 'WIN RATE',      value: `${((portfolio?.win_rate ?? 0)).toFixed(1)}%` },
          { label: '30D RETURN',    value: portfolio?.return_30d_pct != null ? `${portfolio.return_30d_pct >= 0 ? '+' : ''}${portfolio.return_30d_pct.toFixed(2)}%` : '—' },
        ].map(({ label, value }) => (
          <div key={label} style={{ ...card, flex: 1, minWidth: 140, textAlign: 'center' }}>
            <div style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-lg)', fontWeight: 700 }}>{value}</div>
            <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)', marginTop: 'var(--space-1)' }}>{label}</div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
