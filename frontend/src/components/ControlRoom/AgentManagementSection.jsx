import React, { useState } from 'react';
import { Button } from '../Common/Button';
import { Spinner } from '../Common/Spinner';
import useControlRoomStore from '../../stores/controlRoom.store';

const row = {
  display: 'grid',
  gridTemplateColumns: '1fr 120px 80px 100px 160px',
  alignItems: 'center',
  gap: 'var(--space-3)',
  padding: 'var(--space-3) var(--space-4)',
  borderBottom: '1px solid var(--color-border-subtle)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
};

const STATUS_COLOR = {
  running: 'var(--color-agent-running)',
  idle: 'var(--color-agent-idle)',
  paused: 'var(--color-agent-paused)',
  error: 'var(--color-agent-error)',
  stopped: 'var(--color-agent-stopped)',
};

export default function AgentManagementSection() {
  const { agents, loading, startAgent, stopAgent, pauseAgent } = useControlRoomStore();
  const [actionError, setActionError] = useState(null);
  const [busyIds, setBusyIds] = useState(new Set());

  if (loading && agents.length === 0) {
    return <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}><Spinner /></div>;
  }

  const withBusy = (id, fn) => async () => {
    setBusyIds((s) => new Set([...s, id]));
    setActionError(null);
    try {
      await fn(id);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusyIds((s) => { const n = new Set(s); n.delete(id); return n; });
    }
  };

  const pnlColor = (v) => (v ?? 0) >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)';

  return (
    <div style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ ...row, background: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-xs)', letterSpacing: '0.08em', borderBottom: '1px solid var(--color-border)' }}>
        <div>AGENT</div>
        <div>STATUS</div>
        <div>P&L</div>
        <div>CONF</div>
        <div>ACTIONS</div>
      </div>

      {agents.length === 0 ? (
        <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
          No agents
        </div>
      ) : (
        agents.map((agent) => {
          const busy = busyIds.has(agent.id);
          const pnl = agent.total_pnl ?? 0;
          const conf = agent.confidence_score ?? 0;
          const color = STATUS_COLOR[agent.status] ?? 'var(--color-text-muted)';
          return (
            <div key={agent.id} style={row}>
              <div style={{ color: 'var(--color-text-primary)' }}>{agent.name}</div>
              <div style={{ color }}>{agent.status}</div>
              <div style={{ color: pnlColor(pnl) }}>{pnl >= 0 ? '+' : ''}{pnl.toFixed(0)}</div>
              <div style={{ color: conf >= 70 ? 'var(--color-accent-primary)' : conf >= 50 ? 'var(--color-accent-warning)' : 'var(--color-accent-danger)' }}>
                {conf}%
              </div>
              <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
                {busy ? (
                  <Spinner size={14} />
                ) : (
                  <>
                    {agent.status !== 'running' && (
                      <Button variant="primary" onClick={withBusy(agent.id, startAgent)} style={{ padding: '2px 8px', fontSize: '0.65rem' }}>
                        Start
                      </Button>
                    )}
                    {agent.status === 'running' && (
                      <Button variant="ghost" onClick={withBusy(agent.id, pauseAgent)} style={{ padding: '2px 8px', fontSize: '0.65rem' }}>
                        Pause
                      </Button>
                    )}
                    {agent.status !== 'stopped' && (
                      <Button variant="danger" onClick={withBusy(agent.id, stopAgent)} style={{ padding: '2px 8px', fontSize: '0.65rem' }}>
                        Stop
                      </Button>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })
      )}

      {actionError && (
        <div style={{ padding: 'var(--space-3) var(--space-4)', color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', borderTop: '1px solid var(--color-border)' }}>
          {actionError}
        </div>
      )}
    </div>
  );
}
