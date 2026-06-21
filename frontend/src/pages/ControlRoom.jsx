import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import useControlRoomStore from '../stores/controlRoom.store';
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

export default function ControlRoom() {
  const [activeTab, setActiveTab] = useState('brokers');
  const { fetchAll, error, clearError } = useControlRoomStore();

  useEffect(() => {
    fetchAll();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'var(--color-bg-primary)',
      fontFamily: 'var(--font-mono)',
    }}>
      {/* Tab bar */}
      <div style={{
        display: 'flex',
        gap: 0,
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-bg-secondary)',
        padding: '0 var(--space-4)',
        flexShrink: 0,
      }}>
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: 'var(--space-3) var(--space-4)',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid var(--color-accent-primary)' : '2px solid transparent',
              color: activeTab === tab.key ? 'var(--color-accent-primary)' : 'var(--color-text-secondary)',
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--font-size-sm)',
              cursor: 'pointer',
              letterSpacing: '0.05em',
              transition: 'color var(--transition-fast)',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Global error banner */}
      {error && (
        <div style={{
          background: 'var(--color-bg-elevated)',
          borderBottom: '1px solid var(--color-accent-danger)',
          padding: 'var(--space-2) var(--space-4)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-accent-danger)',
        }}>
          <span>⚠ {error}</span>
          <button onClick={clearError} style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: 'var(--font-size-sm)' }}>
            ✕
          </button>
        </div>
      )}

      {/* Section content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-6)' }}>
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
