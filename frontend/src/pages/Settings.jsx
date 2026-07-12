import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useTheme } from '../contexts/ThemeContext';
import { useNavigate } from 'react-router-dom';

/* ── Shared style fragments ───────────────── */
const section = {
  border: '1px solid var(--border-primary)',
  borderRadius: 'var(--radius-md)',
  padding: '1.25rem',
  background: 'var(--bg-secondary)',
  marginBottom: '1rem',
};
const label = { color: 'var(--text-secondary)', fontSize: '11px', fontFamily: 'var(--font-mono)', marginBottom: '0.35rem' };
const input = {
  width: '100%',
  padding: '0.45rem 0.6rem',
  background: 'var(--bg-primary)',
  border: '1px solid var(--border-primary)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: '12px',
  outline: 'none',
};
const toggle = {
  padding: '0.5rem 1rem',
  background: 'transparent',
  border: '1px solid var(--border-primary)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: '12px',
  cursor: 'pointer',
};
const row = { display: 'flex', gap: '1rem', flexWrap: 'wrap' };

export default function Settings() {
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  // Local-only state (persist later via API)
  const [tradingLimit, setTradingLimit] = useState(5000);
  const [maxAgents, setMaxAgents] = useState(5);
  const [emailAlerts, setEmailAlerts] = useState(false);
  const [pushAlerts, setPushAlerts] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{ fontFamily: 'var(--font-mono)', maxWidth: 700, display: 'flex', flexDirection: 'column', gap: '1rem' }}
    >
      <h2 style={{ color: 'var(--text-primary)', fontSize: '18px', margin: 0, fontFamily: 'var(--font-sans)' }}>Settings</h2>

      {/* ── Theme ── */}
      <div style={section}>
        <h3 style={{ color: 'var(--text-primary)', fontSize: '13px', margin: '0 0 0.75rem 0' }}>Theme</h3>
        <div style={row}>
          <button
            onClick={toggleTheme}
            style={{
              ...toggle,
              background: theme === 'dark' ? 'var(--bg-tertiary)' : 'var(--bg-primary)',
              borderColor: theme === 'dark' ? 'var(--accent-primary)' : 'var(--border-primary)',
            }}
          >
            {theme === 'dark' ? '🌙 Dark' : '☀️ Light'}
          </button>
          <span style={{ color: 'var(--text-muted)', fontSize: '11px', alignSelf: 'center' }}>
            Current: {theme === 'dark' ? 'Dark mode' : 'Light mode'}
          </span>
        </div>
      </div>

      {/* ── Notifications ── */}
      <div style={section}>
        <h3 style={{ color: 'var(--text-primary)', fontSize: '13px', margin: '0 0 0.75rem 0' }}>Notifications</h3>
        <div style={row}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '12px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={emailAlerts}
              onChange={() => setEmailAlerts(!emailAlerts)}
              style={{ accentColor: 'var(--accent-primary)' }}
            />
            Email alerts
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '12px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={pushAlerts}
              onChange={() => setPushAlerts(!pushAlerts)}
              style={{ accentColor: 'var(--accent-primary)' }}
            />
            Push notifications
          </label>
        </div>
      </div>

      {/* ── Trading Limits ── */}
      <div style={section}>
        <h3 style={{ color: 'var(--text-primary)', fontSize: '13px', margin: '0 0 0.75rem 0' }}>Trading Limits</h3>
        <div style={row}>
          <div style={{ flex: 1, minWidth: 150 }}>
            <div style={label}>Max position size ($)</div>
            <input
              type="number"
              value={tradingLimit}
              onChange={e => setTradingLimit(Number(e.target.value))}
              style={input}
              min={100}
              step={100}
            />
          </div>
          <div style={{ flex: 1, minWidth: 150 }}>
            <div style={label}>Max concurrent agents</div>
            <input
              type="number"
              value={maxAgents}
              onChange={e => setMaxAgents(Number(e.target.value))}
              style={input}
              min={1}
              max={20}
            />
          </div>
        </div>
      </div>

      {/* ── API / LLM Config ── */}
      <div style={section}>
        <h3 style={{ color: 'var(--text-primary)', fontSize: '13px', margin: '0 0 0.75rem 0' }}>API & LLM Configuration</h3>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
            Configure LLM provider, model, and API keys
          </span>
          <button
            onClick={() => navigate('/control-room')}
            style={{
              padding: '0.4rem 0.75rem',
              background: 'var(--accent-secondary)',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              color: '#fff',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer',
            }}
          >
            Open Control Room
          </button>
        </div>
      </div>

      {/* ── Agent Defaults ── */}
      <div style={section}>
        <h3 style={{ color: 'var(--text-primary)', fontSize: '13px', margin: '0 0 0.75rem 0' }}>Agent Defaults</h3>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
            Create and customize your trading agents
          </span>
          <button
            onClick={() => navigate('/setup')}
            style={{
              padding: '0.4rem 0.75rem',
              background: 'var(--accent-primary)',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              color: '#fff',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            + Hire Agent
          </button>
        </div>
      </div>
    </motion.div>
  );
}