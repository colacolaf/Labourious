import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import useControlRoomStore from '../stores/controlRoom.store';
import { agentsApi } from '../utils/api-client';
import {
  BrokerSection,
  LLMSection,
  AllocationSection,
  AgentManagementSection,
  RiskSection,
  VaultSection,
} from '../components/ControlRoom';

const TABS = [
  { key: 'brokers',    label: 'Brokers' },
  { key: 'llm',        label: 'LLM' },
  { key: 'allocation', label: 'Allocation' },
  { key: 'agents',     label: 'Agents' },
  { key: 'risk',       label: 'Risk' },
  { key: 'vault',      label: 'Vault' },
];

const SECTION = {
  brokers:    <BrokerSection />,
  llm:        <LLMSection />,
  allocation: <AllocationSection />,
  agents:     <AgentManagementSection />,
  risk:       <RiskSection />,
  vault:      <VaultSection />,
};

const ROOMS = [
  { key: 'day_trading',   label: 'Day Trading Floor',    path: '/warroom/day',       accent: '#93c5fd' },
  { key: 'swing_trading', label: 'Sector Office',        path: '/warroom/swing',     accent: '#f59e0b' },
  { key: 'long_term',     label: 'Investment Office',    path: '/warroom/long-term', accent: '#a5b4fc' },
];

export default function ControlRoom() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('brokers');
  const { fetchAll, error, clearError } = useControlRoomStore();
  const [agents, setAgents] = useState([]);

  useEffect(() => {
    fetchAll();
    agentsApi.list().then(setAgents).catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const runningCount = agents.filter(a => a.status === 'running').length;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'var(--bg-primary)',
      fontFamily: 'var(--font-mono)',
    }}>
      {/* ── Room Quick Access + Agent Status Bar ── */}
      <div style={{
        display: 'flex',
        gap: '0.75rem',
        padding: '0.75rem 1.5rem',
        borderBottom: '1px solid var(--border-primary)',
        background: 'var(--bg-secondary)',
        alignItems: 'center',
        flexWrap: 'wrap',
      }}>
        <span style={{ color: 'var(--text-muted)', fontSize: '11px', marginRight: '0.5rem' }}>
          AGENTS: {runningCount}/{agents.length} running
        </span>
        {ROOMS.map(r => {
          const roomAgents = agents.filter(a => a.room === r.key);
          return (
            <button
              key={r.key}
              onClick={() => navigate(r.path)}
              style={{
                padding: '0.35rem 0.75rem',
                background: 'transparent',
                border: `1px solid ${r.accent}66`,
                borderRadius: 'var(--radius-sm)',
                color: r.accent,
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer',
              }}
            >
              {r.label} ({roomAgents.length})
            </button>
          );
        })}
        <div style={{ flex: 1 }} />
        <button
          onClick={() => navigate('/setup')}
          style={{
            padding: '0.35rem 0.75rem',
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

      {/* ── Tab bar ── */}
      <div style={{
        display: 'flex',
        gap: 0,
        borderBottom: '1px solid var(--border-primary)',
        background: 'var(--bg-secondary)',
        padding: '0 1.5rem',
        flexShrink: 0,
      }}>
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '0.75rem 1rem',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid var(--accent-primary)' : '2px solid transparent',
              color: activeTab === tab.key ? 'var(--accent-primary)' : 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              cursor: 'pointer',
              letterSpacing: '0.05em',
              transition: 'color 0.15s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Error banner ── */}
      {error && (
        <div style={{
          background: 'var(--bg-tertiary)',
          borderBottom: '1px solid var(--accent-danger)',
          padding: '0.5rem 1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '12px',
          color: 'var(--accent-danger)',
        }}>
          <span>⚠ {error}</span>
          <button onClick={clearError} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '12px' }}>
            ✕
          </button>
        </div>
      )}

      {/* ── Section content ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { duration: 0.2, ease: 'easeOut' } }}
            exit={{ opacity: 0, transition: { duration: 0.15 } }}
          >
            {SECTION[activeTab]}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}