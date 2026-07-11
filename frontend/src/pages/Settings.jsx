import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { settingsApi } from '../utils/api-client';
import { useUIStore } from '../stores/ui.store';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const sectionTitle = {
  color: 'var(--color-text-secondary)',
  fontSize: 'var(--font-size-sm)',
  letterSpacing: '0.08em',
  marginBottom: 'var(--space-3)',
};

const inputStyle = {
  background: 'var(--color-bg-tertiary)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-sm)',
  padding: '0.5rem 0.75rem',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
  width: '100%',
  maxWidth: 360,
};

const labelStyle = {
  fontSize: 'var(--font-size-xs)',
  color: 'var(--color-text-muted)',
  letterSpacing: '0.08em',
  display: 'block',
  marginBottom: 'var(--space-1)',
};

const btnStyle = {
  padding: '0.5rem 1.25rem',
  background: 'var(--color-accent-primary)',
  color: 'var(--color-text-inverse)',
  border: 'none',
  borderRadius: 'var(--radius-sm)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
  fontWeight: 600,
  cursor: 'pointer',
};

const toggleTrack = (enabled) => ({
  width: 40,
  height: 22,
  borderRadius: 11,
  background: enabled ? 'var(--color-accent-primary)' : 'var(--color-bg-tertiary)',
  border: `1px solid ${enabled ? 'var(--color-accent-primary)' : 'var(--color-border)'}`,
  position: 'relative',
  cursor: 'pointer',
  transition: 'background 0.15s',
  flexShrink: 0,
});

const toggleKnob = (enabled) => ({
  width: 16,
  height: 16,
  borderRadius: '50%',
  background: enabled ? 'white' : 'var(--color-text-muted)',
  position: 'absolute',
  top: 2,
  left: enabled ? 21 : 2,
  transition: 'left 0.15s',
});

function Toggle({ enabled, onChange, label }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', cursor: 'pointer' }}>
      <div style={toggleTrack(enabled)} onClick={() => onChange(!enabled)}>
        <div style={toggleKnob(enabled)} />
      </div>
      <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>{label}</span>
    </label>
  );
}

export default function Settings() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Notification toggles
  const addToast = useUIStore((s) => s.addToast);

  const [allocations, setAllocations] = useState({ per_agent_max_pct: 25, max_total_exposure_pct: 80 });
  const [darkMode, setDarkMode] = useState(true);
  const [wsEnabled, setWsEnabled] = useState(true);
  const [vaultPassword, setVaultPassword] = useState('');
  const [newVaultPassword, setNewVaultPassword] = useState('');
  const [savingPass, setSavingPass] = useState(false);
  const [savingAlloc, setSavingAlloc] = useState(false);

  const fetchSettings = useCallback(async () => {
    try {
      setLoading(true);
      const data = await settingsApi.get();
      if (data?.allocations) {
        setAllocations({
          per_agent_max_pct: data.allocations.per_agent_max_pct ?? 25,
          max_total_exposure_pct: data.allocations.max_total_exposure_pct ?? 80,
        });
      }
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSettings(); }, [fetchSettings]);

  const handleSaveAllocations = async () => {
    setSavingAlloc(true);
    try {
      await settingsApi.patchAllocation(allocations);
      addToast({ type: 'success', message: 'Allocations saved' });
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingAlloc(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (!vaultPassword.trim() || !newVaultPassword.trim()) return;
    setSavingPass(true);
    try {
      await settingsApi.changePassword({
        current_password: vaultPassword,
        new_password: newVaultPassword,
      });
      setVaultPassword('');
      setNewVaultPassword('');
      addToast({ type: 'success', message: 'Vault password changed' });
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingPass(false);
    }
  };

  if (loading) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ padding: 'var(--space-6)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
        Loading settings...
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      style={{ fontFamily: 'var(--font-mono)', padding: 'var(--space-6)', maxWidth: 720, height: '100%', overflow: 'auto' }}
    >
      <h1 style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-2xl)', fontFamily: 'var(--font-sans)', marginBottom: 'var(--space-6)' }}>
        Settings
      </h1>

      {error && <div style={{ color: 'var(--color-text-danger)', fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-4)' }}>{error}</div>}

      {/* Risk Allocations */}
      <div style={{ ...card, marginBottom: 'var(--space-4)' }}>
        <h2 style={sectionTitle}>RISK ALLOCATIONS</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div>
            <label style={labelStyle}>MAX PER AGENT (%)</label>
            <input
              type="number"
              style={{ ...inputStyle, maxWidth: 120 }}
              value={allocations.per_agent_max_pct}
              onChange={(e) => setAllocations((a) => ({ ...a, per_agent_max_pct: Number(e.target.value) }))}
              min={1} max={100}
            />
          </div>
          <div>
            <label style={labelStyle}>MAX TOTAL EXPOSURE (%)</label>
            <input
              type="number"
              style={{ ...inputStyle, maxWidth: 120 }}
              value={allocations.max_total_exposure_pct}
              onChange={(e) => setAllocations((a) => ({ ...a, max_total_exposure_pct: Number(e.target.value) }))}
              min={1} max={100}
            />
          </div>
          <div>
            <button onClick={handleSaveAllocations} disabled={savingAlloc} style={{ ...btnStyle, opacity: savingAlloc ? 0.5 : 1 }}>
              {savingAlloc ? 'SAVING...' : 'SAVE ALLOCATIONS'}
            </button>
          </div>
        </div>
      </div>

      {/* Preferences */}
      <div style={{ ...card, marginBottom: 'var(--space-4)' }}>
        <h2 style={sectionTitle}>PREFERENCES</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <Toggle enabled={darkMode} onChange={setDarkMode} label="Dark mode (always on)" />
          <Toggle enabled={wsEnabled} onChange={setWsEnabled} label="Real-time WebSocket updates" />
        </div>
      </div>

      {/* Vault Password */}
      <div style={card}>
        <h2 style={sectionTitle}>VAULT PASSWORD</h2>
        <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div>
            <label style={labelStyle}>CURRENT PASSWORD</label>
            <input style={inputStyle} type="password" value={vaultPassword} onChange={(e) => setVaultPassword(e.target.value)} placeholder="Enter current password" />
          </div>
          <div>
            <label style={labelStyle}>NEW PASSWORD</label>
            <input style={inputStyle} type="password" value={newVaultPassword} onChange={(e) => setNewVaultPassword(e.target.value)} placeholder="Enter new password" />
          </div>
          <div>
            <button type="submit" disabled={savingPass || !vaultPassword.trim() || !newVaultPassword.trim()} style={{ ...btnStyle, opacity: savingPass || !vaultPassword.trim() || !newVaultPassword.trim() ? 0.5 : 1 }}>
              {savingPass ? 'CHANGING...' : 'CHANGE VAULT PASSWORD'}
            </button>
          </div>
        </form>
      </div>
    </motion.div>
  );
}