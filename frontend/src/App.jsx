import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import useDashboardStore from './stores/dashboard.store';
import useAgentsStore from './stores/agents.store';
import { ROUTES, POLL_INTERVALS } from './utils/constants';

const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

const pageTransition = { duration: 0.18, ease: 'easeOut' };

function PlaceholderPage({ title }) {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={pageTransition}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        gap: '1rem',
        color: 'var(--color-text-secondary)',
        fontFamily: 'var(--font-mono)',
      }}
    >
      <span style={{ fontSize: '2rem', color: 'var(--color-accent-primary)' }}>⬡</span>
      <h2 style={{ color: 'var(--color-text-primary)', fontSize: '1.25rem' }}>{title}</h2>
      <p style={{ fontSize: '0.75rem' }}>Phase 2 implementation pending</p>
    </motion.div>
  );
}

function AppShell({ children }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'var(--sidebar-width) 1fr',
        gridTemplateRows: 'var(--topbar-height) 1fr',
        height: '100vh',
        background: 'var(--color-bg-primary)',
      }}
    >
      <TopBar />
      <Sidebar />
      <main
        style={{
          gridColumn: 2,
          gridRow: 2,
          overflow: 'auto',
          padding: 'var(--space-6)',
        }}
      >
        {children}
      </main>
    </div>
  );
}

function TopBar() {
  const { backendStatus, backendVersion } = useDashboardStore();

  const statusColor = {
    connected: 'var(--color-accent-primary)',
    disconnected: 'var(--color-accent-danger)',
    degraded: 'var(--color-accent-warning)',
    unknown: 'var(--color-text-muted)',
  }[backendStatus] ?? 'var(--color-text-muted)';

  return (
    <header
      style={{
        gridColumn: '1 / -1',
        gridRow: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 var(--space-6)',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-bg-secondary)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <span style={{ color: 'var(--color-accent-primary)', fontSize: '1.25rem' }}>⬡</span>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            color: 'var(--color-text-primary)',
            letterSpacing: '0.1em',
          }}
        >
          LABOURIOUS
        </span>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--color-text-muted)',
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: statusColor,
            display: 'inline-block',
          }}
        />
        <span style={{ color: statusColor }}>{backendStatus.toUpperCase()}</span>
        {backendVersion && <span>v{backendVersion}</span>}
      </div>
    </header>
  );
}

function Sidebar() {
  const navItems = [
    { label: 'Dashboard', path: ROUTES.DASHBOARD, icon: '◈' },
    { label: 'Agents', path: ROUTES.AGENTS, icon: '◉' },
    { label: 'Trades', path: ROUTES.TRADES, icon: '◇' },
    { label: 'Performance', path: ROUTES.PERFORMANCE, icon: '◆' },
    { label: 'Vault', path: ROUTES.VAULT, icon: '◫' },
    { label: 'Settings', path: ROUTES.SETTINGS, icon: '⊙' },
  ];

  return (
    <nav
      style={{
        gridColumn: 1,
        gridRow: 2,
        borderRight: '1px solid var(--color-border)',
        background: 'var(--color-bg-secondary)',
        padding: 'var(--space-4) 0',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-1)',
      }}
    >
      {navItems.map((item) => (
        <a
          key={item.path}
          href={item.path}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-3)',
            padding: 'var(--space-3) var(--space-6)',
            fontFamily: 'var(--font-mono)',
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-secondary)',
            textDecoration: 'none',
            transition: 'color var(--transition-fast)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = 'var(--color-text-primary)';
            e.currentTarget.style.background = 'var(--color-bg-tertiary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'var(--color-text-secondary)';
            e.currentTarget.style.background = 'transparent';
          }}
        >
          <span style={{ color: 'var(--color-accent-primary)' }}>{item.icon}</span>
          {item.label}
        </a>
      ))}
    </nav>
  );
}

export default function App() {
  const { checkBackendHealth, fetchPortfolioSummary } = useDashboardStore();
  const { fetchAgents } = useAgentsStore();

  useEffect(() => {
    checkBackendHealth();
    fetchPortfolioSummary();
    fetchAgents();

    const healthInterval = setInterval(checkBackendHealth, POLL_INTERVALS.HEALTH);
    const portfolioInterval = setInterval(fetchPortfolioSummary, POLL_INTERVALS.PORTFOLIO);
    const agentsInterval = setInterval(fetchAgents, POLL_INTERVALS.AGENTS);

    return () => {
      clearInterval(healthInterval);
      clearInterval(portfolioInterval);
      clearInterval(agentsInterval);
    };
  }, [checkBackendHealth, fetchPortfolioSummary, fetchAgents]);

  return (
    <BrowserRouter>
      <AppShell>
        <AnimatePresence mode="wait">
          <Routes>
            <Route path={ROUTES.DASHBOARD} element={<PlaceholderPage title="Dashboard" />} />
            <Route path={ROUTES.AGENTS} element={<PlaceholderPage title="Agents" />} />
            <Route path={ROUTES.TRADES} element={<PlaceholderPage title="Trades" />} />
            <Route path={ROUTES.PERFORMANCE} element={<PlaceholderPage title="Performance" />} />
            <Route path={ROUTES.VAULT} element={<PlaceholderPage title="Vault" />} />
            <Route path={ROUTES.SETTINGS} element={<PlaceholderPage title="Settings" />} />
            <Route path="*" element={<Navigate to={ROUTES.DASHBOARD} replace />} />
          </Routes>
        </AnimatePresence>
      </AppShell>
    </BrowserRouter>
  );
}
