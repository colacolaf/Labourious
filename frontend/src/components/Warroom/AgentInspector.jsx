import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import useAgentsStore from '../../stores/agents.store';
import { tradesApi, performanceApi } from '../../utils/api-client';
import LLMTab from './LLMTab';

const TABS = ['Overview', 'Trades', 'Rules', 'Performance', 'Settings', 'LLM'];

function Row({ label, value, valueColor }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.8rem' }}>
      <span style={{ color: 'var(--color-text-muted)' }}>{label}</span>
      <span style={{ color: valueColor ?? 'var(--color-text-primary)' }}>{value ?? '—'}</span>
    </div>
  );
}

function OverviewTab({ agent }) {
  const pnl = agent.total_pnl ?? 0;
  const conf = agent.confidence_score ?? 10;
  const confColor = conf >= 70 ? 'var(--color-accent-primary)' : conf >= 35 ? '#ff8c00' : 'var(--color-danger, #ff4444)';
  return (
    <div>
      <Row label="Status" value={agent.status?.toUpperCase()} valueColor={agent.status === 'running' ? 'var(--color-accent-primary)' : undefined} />
      <Row label="P&L" value={`${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`} valueColor={pnl >= 0 ? 'var(--color-accent-primary)' : '#ff4444'} />
      <Row label="Confidence" value={`${conf}%`} valueColor={confColor} />
      <Row label="Win Rate" value={agent.win_rate != null ? `${agent.win_rate.toFixed(1)}%` : '—'} />
      <Row label="Total Trades" value={agent.total_trades ?? 0} />
      <Row label="Consec. Losses" value={agent.consecutive_losses ?? 0} valueColor={(agent.consecutive_losses ?? 0) >= 3 ? '#ff4444' : undefined} />
      <Row label="Symbol" value={agent.symbol} />
      <Row label="Broker" value={agent.broker} />
      <Row label="Mode" value={agent.is_paper_trading ? 'Paper' : 'Live'} />
      <Row label="Paper Balance" value={agent.paper_trading_balance != null ? `$${agent.paper_trading_balance.toFixed(2)}` : '—'} />
    </div>
  );
}

function TradesTab({ agentId }) {
  const [trades, setTrades] = useState([]);
  useEffect(() => {
    tradesApi.getByAgent(agentId).then(setTrades).catch(() => {});
  }, [agentId]);

  if (!trades.length) return <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', marginTop: '1rem' }}>No trades yet.</div>;
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
        <thead>
          <tr style={{ color: 'var(--color-text-muted)', borderBottom: '1px solid var(--color-border)' }}>
            {['Symbol', 'Side', 'Qty', 'Entry', 'P&L', 'Status'].map((h) => (
              <th key={h} style={{ textAlign: 'left', padding: '0.3rem 0.4rem', fontWeight: 'normal' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {trades.slice(0, 20).map((t) => {
            const pnl = t.pnl;
            return (
              <tr key={t.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                <td style={{ padding: '0.35rem 0.4rem' }}>{t.symbol}</td>
                <td style={{ padding: '0.35rem 0.4rem', color: t.side === 'buy' ? 'var(--color-accent-primary)' : '#ff4444' }}>{t.side?.toUpperCase()}</td>
                <td style={{ padding: '0.35rem 0.4rem' }}>{t.quantity}</td>
                <td style={{ padding: '0.35rem 0.4rem' }}>${t.entry_price?.toFixed(2)}</td>
                <td style={{ padding: '0.35rem 0.4rem', color: pnl == null ? 'var(--color-text-muted)' : pnl >= 0 ? 'var(--color-accent-primary)' : '#ff4444' }}>
                  {pnl != null ? `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}` : '—'}
                </td>
                <td style={{ padding: '0.35rem 0.4rem', color: 'var(--color-text-muted)' }}>{t.status}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RulesTab({ agent }) {
  const content = agent.strategy_config?.context_content
    ?? agent.strategy_config?.context
    ?? agent.strategy_config?.rules
    ?? null;
  if (!content) return (
    <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', marginTop: '1rem' }}>
      No context file — agent uses default LLM reasoning
    </div>
  );
  return (
    <pre style={{
      fontSize: '0.75rem', color: 'var(--color-text-secondary)',
      background: 'var(--color-bg-tertiary)', padding: '0.75rem',
      borderRadius: 4, overflowX: 'auto', whiteSpace: 'pre-wrap', marginTop: '0.5rem',
    }}>
      {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
    </pre>
  );
}

function PerformanceTab({ agentId }) {
  const [perf, setPerf] = useState([]);
  useEffect(() => {
    performanceApi.byAgent(agentId).then(setPerf).catch(() => {});
  }, [agentId]);

  if (!perf.length) return <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', marginTop: '1rem' }}>No performance data yet.</div>;
  const chartData = perf.slice(0, 50).reverse().map((p) => ({ date: p.timestamp?.slice(0, 10), pnl: p.total_pnl }));
  return (
    <ResponsiveContainer width="100%" height={160}>
      <LineChart data={chartData}>
        <XAxis dataKey="date" tick={{ fontSize: 8, fill: 'var(--color-text-muted)' }} hide />
        <YAxis tick={{ fontSize: 8, fill: 'var(--color-text-muted)' }} />
        <Tooltip contentStyle={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', fontFamily: 'var(--font-mono)', fontSize: 10 }} />
        <Line type="monotone" dataKey="pnl" stroke="var(--color-accent-primary, #00ff88)" dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function SettingsTab({ agent }) {
  const { updateAgent } = useAgentsStore();
  const [busy, setBusy] = useState(false);
  const [local, setLocal] = useState({
    execution_mode: agent.execution_mode ?? 'human_in_loop',
    check_frequency: agent.check_frequency ?? 300,
    max_position_size: agent.max_position_size ?? 1000,
    stop_loss_pct: agent.stop_loss_pct ?? 2.0,
    take_profit_pct: agent.take_profit_pct ?? 4.0,
  });

  // Sync local state when agent prop changes (e.g., WS update)
  useEffect(() => {
    setLocal({
      execution_mode: agent.execution_mode ?? 'human_in_loop',
      check_frequency: agent.check_frequency ?? 300,
      max_position_size: agent.max_position_size ?? 1000,
      stop_loss_pct: agent.stop_loss_pct ?? 2.0,
      take_profit_pct: agent.take_profit_pct ?? 4.0,
    });
  }, [agent.id, agent.execution_mode, agent.check_frequency, agent.max_position_size, agent.stop_loss_pct, agent.take_profit_pct]);

  const save = async () => {
    setBusy(true);
    await updateAgent(agent.id, local).catch(() => {});
    setBusy(false);
  };

  const toggle = async (field) => {
    setBusy(true);
    await updateAgent(agent.id, { [field]: !agent[field] }).catch(() => {});
    setBusy(false);
  };

  const field = (label, key, type = 'number') => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.4rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.8rem' }}>
      <span style={{ color: 'var(--color-text-muted)' }}>{label}</span>
      <input
        type={type}
        value={local[key]}
        onChange={(e) => setLocal((p) => ({ ...p, [key]: type === 'number' ? parseFloat(e.target.value) : e.target.value }))}
        style={{
          width: 80, background: 'var(--color-bg-tertiary)',
          border: '1px solid var(--color-border)', color: 'var(--color-text-primary)',
          fontFamily: 'var(--font-mono)', fontSize: '0.75rem', padding: '0.2rem 0.4rem',
        }}
      />
    </div>
  );

  const btnStyle = (danger) => ({
    padding: '0.3rem 0.7rem', fontFamily: 'var(--font-mono)', fontSize: '0.7rem',
    cursor: 'pointer', background: 'transparent',
    border: `1px solid ${danger ? 'var(--color-danger, #ff4444)' : 'var(--color-accent-primary, #00ff88)'}`,
    color: danger ? 'var(--color-danger, #ff4444)' : 'var(--color-accent-primary)',
    borderRadius: 3,
  });

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.4rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.8rem' }}>
        <span style={{ color: 'var(--color-text-muted)' }}>Execution Mode</span>
        <select
          value={local.execution_mode}
          onChange={(e) => setLocal((p) => ({ ...p, execution_mode: e.target.value }))}
          style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}
        >
          <option value="autonomous">Autonomous</option>
          <option value="human_in_loop">Human-in-Loop</option>
          <option value="risk_based">Risk-Based</option>
        </select>
      </div>
      {field('Check Freq (s)', 'check_frequency')}
      {field('Max Position $', 'max_position_size')}
      {field('Stop Loss %', 'stop_loss_pct')}
      {field('Take Profit %', 'take_profit_pct')}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.8rem' }}>
        <span style={{ color: 'var(--color-text-muted)' }}>Active</span>
        <button disabled={busy} onClick={() => toggle('is_active')} style={btnStyle(!agent.is_active)}>
          {agent.is_active ? 'Disable' : 'Enable'}
        </button>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.8rem' }}>
        <span style={{ color: 'var(--color-text-muted)' }}>Paper Trading</span>
        <button disabled={busy} onClick={() => toggle('is_paper_trading')} style={btnStyle(agent.is_paper_trading)}>
          {agent.is_paper_trading ? 'Switch Live' : 'Switch Paper'}
        </button>
      </div>
      <div style={{ marginTop: '1rem' }}>
        <button
          onClick={save}
          disabled={busy}
          style={{ width: '100%', padding: '0.5rem', background: 'var(--color-accent-primary, #00ff88)', color: '#000', border: 'none', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer', borderRadius: 3 }}
        >
          {busy ? 'SAVING…' : 'SAVE SETTINGS'}
        </button>
      </div>
    </div>
  );
}

export default function AgentInspector({ agent, onClose }) {
  const [tab, setTab] = useState('Overview');

  // Reset tab when agent changes
  useEffect(() => { setTab('Overview'); }, [agent?.id]);

  return (
    <AnimatePresence>
      {agent && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{ position: 'fixed', inset: 0, zIndex: 200 }}
          />
          {/* Panel */}
          <motion.div
            initial={{ x: 380 }}
            animate={{ x: 0 }}
            exit={{ x: 380 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            style={{
              position: 'fixed',
              top: 'var(--topbar-height, 48px)',
              right: 0,
              bottom: 0,
              width: 380,
              background: 'var(--color-bg-secondary)',
              borderLeft: '1px solid var(--color-border)',
              zIndex: 201,
              display: 'flex',
              flexDirection: 'column',
              fontFamily: 'var(--font-mono)',
              overflow: 'hidden',
            }}
          >
            {/* Header */}
            <div style={{ padding: '1rem', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--color-accent-primary)', letterSpacing: '0.1em' }}>AGENT INSPECTOR</div>
                <div style={{ fontSize: '1rem', color: 'var(--color-text-primary)', marginTop: 2 }}>{agent.name}</div>
              </div>
              <button
                onClick={onClose}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)', fontSize: '1.2rem' }}
              >
                ×
              </button>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
              {TABS.map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  style={{
                    flex: 1,
                    padding: '0.6rem 0',
                    background: 'none',
                    border: 'none',
                    borderBottom: tab === t ? '2px solid var(--color-accent-primary)' : '2px solid transparent',
                    color: tab === t ? 'var(--color-accent-primary)' : 'var(--color-text-muted)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.65rem',
                    cursor: 'pointer',
                    letterSpacing: '0.05em',
                  }}
                >
                  {t.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
              {tab === 'Overview' && <OverviewTab agent={agent} />}
              {tab === 'Trades' && <TradesTab agentId={agent.id} />}
              {tab === 'Rules' && <RulesTab agent={agent} />}
              {tab === 'Performance' && <PerformanceTab agentId={agent.id} />}
              {tab === 'Settings' && <SettingsTab agent={agent} />}
              {tab === 'LLM' && <LLMTab agent={agent} />}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
