import { useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import useDashboardStore from '../stores/dashboard.store';
import useAgentsStore from '../stores/agents.store';
import RecentTradesFeed from '../components/RecentTradesFeed';
import SystemHealthPanel from '../components/SystemHealthPanel';

const card = (label, value, color = 'var(--color-text-primary)') => (
  <div
    key={label}
    style={{
      background: 'var(--color-bg-secondary)',
      border: '1px solid var(--color-border)',
      borderRadius: 6,
      padding: '1rem 1.25rem',
      fontFamily: 'var(--font-mono)',
    }}
  >
    <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', marginBottom: 6, letterSpacing: '0.1em' }}>
      {label.toUpperCase()}
    </div>
    <div style={{ fontSize: '1.5rem', fontWeight: 700, color }}>{value}</div>
  </div>
);

function fmt(n) {
  if (n == null) return '—';
  const abs = Math.abs(n);
  const s = abs >= 1000 ? `$${(abs / 1000).toFixed(1)}k` : `$${abs.toFixed(2)}`;
  return n < 0 ? `-${s}` : `+${s}`;
}

export default function Dashboard() {
  const {
    portfolio, portfolioHistory, recentTrades,
    backendStatus, dbStatus, backendVersion, backendUptime,
    fetchPortfolioSummary, fetchPortfolioHistory, fetchRecentTrades, fetchSystemHealth,
  } = useDashboardStore();
  const { agents, fetchAgents } = useAgentsStore();

  useEffect(() => {
    fetchPortfolioSummary();
    fetchPortfolioHistory();
    fetchAgents();
    fetchRecentTrades(20);
    fetchSystemHealth();
  }, [fetchPortfolioSummary, fetchPortfolioHistory, fetchAgents, fetchRecentTrades, fetchSystemHealth]);

  const pnlColor = portfolio.totalPnl >= 0 ? 'var(--color-accent-primary)' : 'var(--color-accent-danger, #ff4444)';

  const leaderboard = [...agents]
    .sort((a, b) => (b.total_pnl ?? 0) - (a.total_pnl ?? 0))
    .slice(0, 10);

  return (
    <div style={{ fontFamily: 'var(--font-mono)', padding: '0 0 2rem' }}>
      <div style={{ fontSize: '0.65rem', color: 'var(--color-accent-primary)', letterSpacing: '0.15em', marginBottom: '1.25rem' }}>
        PORTFOLIO OVERVIEW
      </div>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        {card('Total P&L', fmt(portfolio.totalPnl), pnlColor)}
        {card('Active Agents', portfolio.activeAgents)}
        {card('Total Trades', portfolio.totalTrades)}
        {card('Win Rate', portfolio.winRate != null ? `${portfolio.winRate.toFixed(1)}%` : '—')}
      </div>

      {/* Equity curve */}
      {portfolioHistory.length > 0 && (
        <div style={{
          background: 'var(--color-bg-secondary)',
          border: '1px solid var(--color-border)',
          borderRadius: 6,
          padding: '1rem',
          marginBottom: '2rem',
        }}>
          <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', letterSpacing: '0.1em', marginBottom: '1rem' }}>
            30-DAY EQUITY CURVE
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={portfolioHistory}>
              <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--color-text-muted)' }} />
              <YAxis tick={{ fontSize: 9, fill: 'var(--color-text-muted)' }} />
              <Tooltip
                contentStyle={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', fontFamily: 'var(--font-mono)', fontSize: 11 }}
              />
              <Line type="monotone" dataKey="pnl" stroke="var(--color-accent-primary, #00ff88)" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Agent leaderboard */}
      {leaderboard.length > 0 && (
        <div style={{
          background: 'var(--color-bg-secondary)',
          border: '1px solid var(--color-border)',
          borderRadius: 6,
          padding: '1rem',
          marginBottom: '2rem',
        }}>
          <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', letterSpacing: '0.1em', marginBottom: '1rem' }}>
            AGENT LEADERBOARD
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
            <thead>
              <tr style={{ color: 'var(--color-text-muted)', borderBottom: '1px solid var(--color-border)' }}>
                {['Agent', 'Symbol', 'P&L', 'Win%', 'Trades', 'Status'].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '0.4rem 0.5rem', fontWeight: 'normal', fontSize: '0.65rem', letterSpacing: '0.08em' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((a) => {
                const pnl = a.total_pnl ?? 0;
                const c = pnl >= 0 ? 'var(--color-accent-primary)' : '#ff4444';
                return (
                  <tr key={a.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '0.5rem', color: 'var(--color-text-primary)' }}>{a.name}</td>
                    <td style={{ padding: '0.5rem', color: 'var(--color-text-muted)' }}>{a.symbol}</td>
                    <td style={{ padding: '0.5rem', color: c }}>{fmt(pnl)}</td>
                    <td style={{ padding: '0.5rem' }}>{a.win_rate?.toFixed(1) ?? '—'}%</td>
                    <td style={{ padding: '0.5rem' }}>{a.total_trades ?? 0}</td>
                    <td style={{ padding: '0.5rem', color: a.status === 'running' ? 'var(--color-accent-primary)' : 'var(--color-text-muted)' }}>{a.status?.toUpperCase() ?? '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Bottom row: leaderboard + health side-by-side, trades full width */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', borderRadius: 6, overflow: 'hidden' }}>
          <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', letterSpacing: '0.1em', padding: '0.75rem 1rem 0' }}>
            RECENT TRADES
          </div>
          <RecentTradesFeed trades={recentTrades} />
        </div>
        <div style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '0.75rem 1rem' }}>
          <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', letterSpacing: '0.1em', marginBottom: '0.75rem' }}>
            SYSTEM HEALTH
          </div>
          <SystemHealthPanel
            backendStatus={backendStatus}
            dbStatus={dbStatus}
            backendVersion={backendVersion}
            backendUptime={backendUptime}
          />
        </div>
      </div>
    </div>
  );
}
