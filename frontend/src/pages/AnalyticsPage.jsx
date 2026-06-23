import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import useAnalyticsStore from '../stores/analytics.store';
import useAgentsStore from '../stores/agents.store';
import EquityChart from '../components/Analytics/EquityChart';
import AgentLeaderboard from '../components/Analytics/AgentLeaderboard';
import CorrelationMatrix from '../components/Analytics/CorrelationMatrix';
import AttributionWaterfall from '../components/Analytics/AttributionWaterfall';
import BacktestRunner from '../components/Analytics/BacktestRunner';
import BacktestHistory from '../components/Analytics/BacktestHistory';

const sectionStyle = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-6)',
  marginBottom: 'var(--space-6)',
};

const sectionHeader = {
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-xs)',
  letterSpacing: '0.12em',
  color: 'var(--color-text-muted)',
  marginBottom: 'var(--space-4)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
};

const kpiBox = (label, value, color) => (
  <div key={label} style={{
    background: 'var(--color-bg-elevated)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)',
    padding: 'var(--space-4) var(--space-6)',
    minWidth: 120,
  }}>
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: 4, letterSpacing: '0.08em' }}>{label}</div>
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xl)', fontWeight: 700, color: color ?? 'var(--color-text-primary)' }}>{value}</div>
  </div>
);

const TIME_RANGES = [
  { label: '7D', days: 7 },
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
  { label: 'ALL', days: 365 },
];

export default function AnalyticsPage() {
  const {
    portfolio, equityCurve, leaderboard, leaderboardSort,
    correlation, attribution,
    fetchPortfolio, fetchEquityCurve, fetchLeaderboard,
    fetchCorrelation, fetchAttribution,
  } = useAnalyticsStore();
  const { agents, fetchAgents } = useAgentsStore();

  const [activeDays, setActiveDays] = useState(30);

  useEffect(() => {
    fetchPortfolio();
    fetchEquityCurve(activeDays);
    fetchLeaderboard(leaderboardSort);
    fetchCorrelation();
    fetchAttribution();
    fetchAgents();
  }, [activeDays, fetchPortfolio, fetchEquityCurve, fetchLeaderboard, leaderboardSort, fetchCorrelation, fetchAttribution, fetchAgents]);

  const handleDaysChange = (days) => {
    setActiveDays(days);
  };

  const p = portfolio;
  const totalPnlColor = p?.total_pnl >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
    >
      {/* Portfolio Performance */}
      <div style={sectionStyle}>
        <div style={sectionHeader}>
          <span>PORTFOLIO PERFORMANCE</span>
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            {TIME_RANGES.map(({ label, days }) => (
              <button
                key={label}
                onClick={() => handleDaysChange(days)}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--font-size-xs)',
                  padding: '2px 8px',
                  background: activeDays === days ? 'var(--color-bg-elevated)' : 'transparent',
                  border: `1px solid ${activeDays === days ? 'var(--color-accent-primary)' : 'var(--color-border)'}`,
                  color: activeDays === days ? 'var(--color-accent-primary)' : 'var(--color-text-muted)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                }}
              >{label}</button>
            ))}
          </div>
        </div>

        <EquityChart data={equityCurve} height={200} />

        <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', marginTop: 'var(--space-6)' }}>
          {kpiBox('TOTAL P&L', p ? `${p.total_pnl >= 0 ? '+' : ''}$${p.total_pnl?.toFixed(2) ?? '—'}` : '—', totalPnlColor)}
          {kpiBox('SHARPE', p?.sharpe_ratio != null ? p.sharpe_ratio.toFixed(2) : '—', 'var(--color-accent-secondary)')}
          {kpiBox('MAX DD', p?.max_drawdown != null ? `${(p.max_drawdown * 100).toFixed(1)}%` : '—', 'var(--color-accent-warning)')}
          {kpiBox('WIN RATE', p?.win_rate != null ? `${p.win_rate.toFixed(1)}%` : '—', 'var(--color-text-primary)')}
          {kpiBox('30D RETURN', p?.return_30d_pct != null ? `${p.return_30d_pct >= 0 ? '+' : ''}${p.return_30d_pct.toFixed(2)}%` : '—', p?.return_30d_pct >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)')}
        </div>
      </div>

      {/* Agent Leaderboard */}
      <div style={sectionStyle}>
        <div style={sectionHeader}>
          <span>AGENT LEADERBOARD</span>
        </div>
        <AgentLeaderboard
          rows={leaderboard}
          sortBy={leaderboardSort}
          onSort={(col) => fetchLeaderboard(col)}
        />
      </div>

      {/* Correlation Matrix */}
      <div style={sectionStyle}>
        <div style={sectionHeader}><span>CORRELATION MATRIX</span></div>
        <CorrelationMatrix data={correlation} />
      </div>

      {/* Attribution */}
      <div style={sectionStyle}>
        <div style={sectionHeader}><span>P&L ATTRIBUTION</span></div>
        <AttributionWaterfall data={attribution} />
      </div>

      {/* Backtest Runner */}
      <div style={sectionStyle}>
        <div style={sectionHeader}><span>BACKTEST</span></div>
        <BacktestRunner agents={agents} />
        <BacktestHistory agentId={null} />
      </div>
    </motion.div>
  );
}
