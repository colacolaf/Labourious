import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import useDashboardStore from './stores/dashboard.store';
import useAgentsStore from './stores/agents.store';
import useWizardStore from './stores/wizard.store';
import useAuthStore from './stores/auth.store';
import { useWebSocket } from './hooks/useWebSocket';
import { POLL_INTERVALS } from './utils/constants';
import WizardShell from './components/Wizard/WizardShell';
import ProtectedRoute from './components/ProtectedRoute';

// Pages
import Dashboard from './pages/Dashboard';
import WarroomDay from './pages/WarroomDay';
import WarroomSwing from './pages/WarroomSwing';
import WarroomLongTerm from './pages/WarroomLongTerm';
import AnalyticsPage from './pages/AnalyticsPage';
import NotificationsPage from './pages/NotificationsPage';
import ContextBuilder from './components/Warroom/ContextBuilder';
import Lobby from './pages/Lobby';
import Login from './pages/Login';
import OfficeEditor from './pages/OfficeEditor';
import CharacterCustomizer from './pages/CharacterCustomizer';
import Trades from './pages/Trades';
import VaultSettings from './pages/VaultSettings';
import Settings from './pages/Settings';

const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};
const pageTransition = { duration: 0.18, ease: 'easeOut' };

function AppShell({ children }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'var(--sidebar-width, 200px) 1fr',
        gridTemplateRows: 'var(--topbar-height, 48px) 1fr',
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
          padding: 'var(--space-6, 1.5rem)',
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
    connected: 'var(--color-text-accent)',
    disconnected: 'var(--color-accent-danger, #ff4444)',
    degraded: 'var(--color-accent-warning, #ffb020)',
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
        padding: '0 var(--space-6, 1.5rem)',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-bg-secondary)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3, 0.75rem)' }}>
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
          gap: 'var(--space-2, 0.5rem)',
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--font-size-xs, 0.7rem)',
          color: 'var(--color-text-muted)',
        }}
      >
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: statusColor, display: 'inline-block' }} />
        <span style={{ color: statusColor }}>{backendStatus.toUpperCase()}</span>
        {backendVersion && <span>v{backendVersion}</span>}
      </div>
    </header>
  );
}

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/', icon: '◈', end: true },
  { label: 'Lobby', path: '/lobby', icon: '⬡' },
  { label: 'Day Trading Floor', path: '/warroom/day' },
  { label: 'Sector Office', path: '/warroom/swing' },
  { label: 'Investment Office', path: '/warroom/long' },
  { label: 'Analytics', path: '/analytics', icon: '◈' },
  { label: 'New Agent', path: '/agents/new', icon: '✦' },
  { label: 'Trades', path: '/trades', icon: '◇' },
  { label: 'Vault', path: '/vault', icon: '◫' },
  { label: 'Settings', path: '/settings', icon: '⊙' },
  { label: 'Notifications', path: '/settings/notifications', icon: '◆' },
];

function Sidebar() {
  return (
    <nav
      style={{
        gridColumn: 1,
        gridRow: 2,
        borderRight: '1px solid var(--color-border)',
        background: 'var(--color-bg-secondary)',
        padding: 'var(--space-4, 1rem) 0',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-1, 0.25rem)',
        overflowY: 'auto',
      }}
    >
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          end={item.end}
          style={({ isActive }) => ({
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-3, 0.75rem)',
            padding: 'var(--space-3, 0.75rem) var(--space-6, 1.5rem)',
            fontFamily: 'var(--font-mono)',
            fontSize: 'var(--font-size-sm, 0.8rem)',
            color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
            textDecoration: 'none',
            background: isActive ? 'var(--color-bg-tertiary)' : 'transparent',
            borderLeft: isActive ? '2px solid var(--color-accent-primary)' : '2px solid transparent',
            transition: 'all 0.12s',
          })}
        >
          {item.icon && <span style={{ color: 'var(--color-text-accent)' }}>{item.icon}</span>}
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

// Initialise WS at app level (singleton)
function WSInitialiser() {
  useWebSocket();
  return null;
}

export default function App() {
  const { checkBackendHealth, fetchPortfolioSummary } = useDashboardStore();
  const { fetchAgents } = useAgentsStore();
  const isComplete = useWizardStore((s) => s.isComplete);
  const loadFromStorage = useAuthStore((s) => s.loadFromStorage);
  const [showWizard, setShowWizard] = useState(() => !localStorage.getItem('wizard_complete'));

  // Rehydrate auth tokens on boot
  useEffect(() => { loadFromStorage(); }, [loadFromStorage]);

  useEffect(() => {
    if (isComplete) {
      localStorage.setItem('wizard_complete', '1');
      setShowWizard(false);
    }
  }, [isComplete]);

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
      <WSInitialiser />
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />

        {/* Protected — AppShell + wizard overlay */}
        <Route element={<ProtectedRoute />}>
          <Route path="*" element={
            <>
              {showWizard && <WizardShell />}
              <AppShell>
                <AnimatePresence mode="wait">
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/lobby" element={<Lobby />} />
                    <Route path="/warroom/day" element={<WarroomDay />} />
                    <Route path="/warroom/swing" element={<WarroomSwing />} />
                    <Route path="/warroom/long" element={<WarroomLongTerm />} />
                    <Route path="/editor/room/:roomKey" element={<OfficeEditor />} />
                    <Route path="/editor/character" element={<CharacterCustomizer />} />
                    <Route path="/editor/character/:agentId" element={<CharacterCustomizer />} />
                    <Route path="/analytics" element={
                      <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={pageTransition}>
                        <AnalyticsPage />
                      </motion.div>
                    } />
                    <Route path="/agents/new" element={
                      <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={pageTransition}>
                        <ContextBuilder />
                      </motion.div>
                    } />
                    <Route path="/trades" element={
                      <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={pageTransition}>
                        <Trades />
                      </motion.div>
                    } />
                    <Route path="/vault" element={
                      <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={pageTransition}>
                        <VaultSettings />
                      </motion.div>
                    } />
                    <Route path="/settings" element={
                      <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={pageTransition}>
                        <Settings />
                      </motion.div>
                    } />
                    <Route path="/settings/notifications" element={<NotificationsPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </AnimatePresence>
              </AppShell>
            </>
          } />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}