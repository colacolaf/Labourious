import React, { useState, useEffect } from 'react';
import { Button } from '../Common/Button';
import { Spinner } from '../Common/Spinner';
import useControlRoomStore from '../../stores/controlRoom.store';
import { agentsApi } from '../../utils/api-client';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const row = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: 'var(--space-3) 0',
  borderBottom: '1px solid var(--color-border-subtle)',
};

export default function RiskSection() {
  const { settings, loading, saving, saveAllocation } = useControlRoomStore();
  const alloc = settings?.allocation;

  const [stopping, setStopping] = useState(false);
  const [stopResult, setStopResult] = useState(null);
  const [drawdown, setDrawdown] = useState(0.25);
  const [posSize, setPosSize] = useState(0.05);
  const [maxAgents, setMaxAgents] = useState(20);
  const [saveError, setSaveError] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (alloc) {
      setDrawdown(alloc.max_portfolio_drawdown ?? 0.25);
      setPosSize(alloc.default_position_size ?? 0.05);
      setMaxAgents(alloc.max_agents ?? 20);
    }
  }, [alloc]);

  if (loading && !settings) {
    return <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}><Spinner /></div>;
  }

  const handleSave = async (e) => {
    e.preventDefault();
    setSaveError(null);
    setSaved(false);
    try {
      await saveAllocation({ max_portfolio_drawdown: drawdown, default_position_size: posSize, max_agents: maxAgents });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setSaveError(err.message);
    }
  };

  const pct = (v) => `${(v * 100).toFixed(0)}%`;

  const handleEmergencyStop = async () => {
    if (!window.confirm('EMERGENCY STOP: pause all agents immediately?')) return;
    setStopping(true);
    setStopResult(null);
    try {
      const result = await agentsApi.emergencyStop();
      setStopResult(result);
    } catch (err) {
      setStopResult({ error: err.message });
    } finally {
      setStopping(false);
    }
  };

  return (
    <form onSubmit={handleSave} style={card}>
      {/* Current values summary */}
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-xs)', letterSpacing: '0.08em', marginBottom: 'var(--space-3)' }}>
          CURRENT RISK PARAMETERS
        </div>
        <div style={row}>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>Hard Drawdown Limit</span>
          <span style={{ color: 'var(--color-accent-danger)' }}>{pct(drawdown)}</span>
        </div>
        <div style={row}>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>Default Position Size</span>
          <span style={{ color: 'var(--color-accent-secondary)' }}>{pct(posSize)}</span>
        </div>
        <div style={{ ...row, borderBottom: 'none' }}>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>Max Concurrent Agents</span>
          <span style={{ color: 'var(--color-text-primary)' }}>{maxAgents}</span>
        </div>
      </div>

      {/* Edit */}
      <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-xs)', letterSpacing: '0.08em', marginBottom: 'var(--space-3)' }}>
        ADJUST
      </div>

      <div style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-1)' }}>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>Drawdown limit</span>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-accent-danger)' }}>{pct(drawdown)}</span>
        </div>
        <input type="range" min="0.05" max="0.50" step="0.01" value={drawdown}
          onChange={(e) => setDrawdown(parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--color-accent-danger)' }} />
      </div>

      <div style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-1)' }}>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>Position size</span>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-accent-secondary)' }}>{pct(posSize)}</span>
        </div>
        <input type="range" min="0.01" max="0.20" step="0.01" value={posSize}
          onChange={(e) => setPosSize(parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--color-accent-secondary)' }} />
      </div>

      <div style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-1)' }}>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>Max agents</span>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>{maxAgents}</span>
        </div>
        <input type="range" min="1" max="50" step="1" value={maxAgents}
          onChange={(e) => setMaxAgents(parseInt(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--color-accent-primary)' }} />
      </div>

      {saveError && <div style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)' }}>{saveError}</div>}
      {saved && <div style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)' }}>✓ Saved</div>}

      <Button type="submit" disabled={saving}>
        {saving ? 'Saving…' : 'Save Risk Settings'}
      </Button>

      <div style={{ borderTop: '1px solid var(--color-border)', marginTop: 'var(--space-6)', paddingTop: 'var(--space-4)' }}>
        <button
          type="button"
          onClick={handleEmergencyStop}
          disabled={stopping}
          style={{
            width: '100%', padding: 'var(--space-3)',
            background: stopping ? 'var(--color-bg-tertiary)' : 'var(--color-accent-danger, #ff4444)',
            color: '#fff', border: 'none', fontFamily: 'var(--font-mono)', fontWeight: 700,
            fontSize: 'var(--font-size-sm)', cursor: stopping ? 'not-allowed' : 'pointer',
            borderRadius: 'var(--radius-sm)', letterSpacing: '0.08em',
          }}
        >
          {stopping ? 'STOPPING...' : 'EMERGENCY STOP ALL AGENTS'}
        </button>
        {stopResult && (
          <div style={{ marginTop: 'var(--space-2)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: stopResult.error ? 'var(--color-accent-danger)' : 'var(--color-accent-primary)' }}>
            {stopResult.error ? `Error: ${stopResult.error}` : `Stopped ${stopResult.stopped} agents.`}
          </div>
        )}
      </div>
    </form>
  );
}
