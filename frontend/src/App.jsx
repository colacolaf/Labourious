import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import Wizard from './components/Wizard/WizardShell';
import useDashboardStore from './stores/dashboard.store';

// Pages
import Lobby from './pages/Lobby';
import Dashboard from './pages/Dashboard';
import ControlRoom from './pages/ControlRoom';
import Trades from './pages/Trades';
import AnalyticsPage from './pages/AnalyticsPage';
import VaultSettings from './pages/VaultSettings';
import Settings from './pages/Settings';
import Login from './pages/Login';
import NotFound from './pages/NotFound';
import NotificationsPage from './pages/NotificationsPage';
import CharacterCustomizer from './pages/CharacterCustomizer';
import OfficeEditor from './pages/OfficeEditor';
import WarroomDay from './pages/WarroomDay';
import WarroomSwing from './pages/WarroomSwing';
import WarroomLongTerm from './pages/WarroomLongTerm';

/* ── Sidebar link config ─────────────────── */
const NAV_LINKS = [
  { to: '/lobby', label: 'Lobby', end: false },
  { to: '/control-room', label: 'Control Room' },
  { to: '/warroom/day', label: 'Day Room' },
  { to: '/warroom/swing', label: 'Swing Room' },
  { to: '/warroom/long-term', label: 'Long-Term Room' },
  { to: '/trades', label: 'Trades' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/character', label: 'Character' },
  { to: '/office-editor', label: 'Office Editor' },
  { to: '/vault', label: 'Vault' },
  { to: '/settings', label: 'Settings' },
];

/* ── AppShell ─────────────────────────────── */
function AppShell({ children }) {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'var(--sidebar-width, 200px) 1fr',
        gridTemplateRows: 'var(--topbar-height, 48px) 1fr',
        height: '100vh',
        background: 'var(--bg-primary)',
      }}
    >
      {/* Top bar */}
      <header
        style={{
          gridColumn: '1 / -1',
          gridRow: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 1.5rem',
          borderBottom: '1px solid var(--border-primary)',
          background: 'var(--bg-secondary)',
        }}
      >
        <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '14px' }}>
          LABOURIOUS
        </span>
        <button
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          style={{
            background: 'none',
            border: '1px solid var(--border-primary)',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '4px 10px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12px',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {theme === 'dark' ? '☀' : '☾'}
        </button>
      </header>

      {/* Sidebar */}
      <nav
        style={{
          gridColumn: 1,
          gridRow: 2,
          borderRight: '1px solid var(--border-primary)',
          background: 'var(--bg-secondary)',
          padding: '0.75rem 0',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
        }}
      >
        {NAV_LINKS.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            style={({ isActive }) => ({
              padding: '0.6rem 1.5rem',
              color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
              textDecoration: 'none',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              borderLeft: isActive ? '2px solid var(--accent-primary)' : '2px solid transparent',
              transition: 'color 0.15s, border-color 0.15s',
            })}
          >
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Main content */}
      <main style={{ gridColumn: 2, gridRow: 2, overflow: 'auto', padding: '1.5rem', position: 'relative' }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

/* ── App ──────────────────────────────────── */
function AppRoutes() {
  const checkBackendHealth = useDashboardStore((s) => s.checkBackendHealth);

  useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

  return (
    <Routes>
      {/* Lobby as main landing */}
      <Route path="/" element={<Lobby />} />
      <Route path="/lobby" element={<Lobby />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/control-room" element={<ControlRoom />} />
      <Route path="/warroom/day" element={<WarroomDay />} />
      <Route path="/warroom/swing" element={<WarroomSwing />} />
      <Route path="/warroom/long-term" element={<WarroomLongTerm />} />
      <Route path="/trades" element={<Trades />} />
      <Route path="/analytics" element={<AnalyticsPage />} />
      <Route path="/vault" element={<VaultSettings />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/character" element={<CharacterCustomizer />} />
      <Route path="/office-editor" element={<OfficeEditor />} />
      <Route path="/notifications" element={<NotificationsPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/setup" element={<Wizard />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          {/* Wizard is standalone — no AppShell chrome */}
          <Route path="/setup" element={<Wizard />} />
          {/* Everything else wrapped in AppShell */}
          <Route
            path="*"
            element={
              <AppShell>
                <AppRoutes />
              </AppShell>
            }
          />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}