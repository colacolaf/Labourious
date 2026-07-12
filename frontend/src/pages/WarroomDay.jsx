import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import WarroomPhaserGame from '../components/Warroom/WarroomPhaserGame';
import AgentInspector from '../components/Warroom/AgentInspector';
import useAgentsStore from '../stores/agents.store';

const ROOM_LABELS = { day: 'Day Trading Room', swing: 'Swing Trading Room', longterm: 'Investment Room' };

export default function WarroomDay() {
  const agents = useAgentsStore((s) => s.agents);
  const selectedAgent = useAgentsStore((s) => s.selectedAgent);
  const selectAgent = useAgentsStore((s) => s.selectAgent);

  const handleAgentClick = useCallback(({ agentId } = {}) => {
    const agent = agents.find((a) => a.id === agentId);
    if (agent) selectAgent(agent);
  }, [agents, selectAgent]);

  return (
    <div data-room="day" style={{ position: 'relative', height: '100%', width: '100%', background: 'var(--room-gradient, var(--bg-primary))', overflow: 'hidden' }}>
      {/* Room header */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, zIndex: 5,
        padding: '0.5rem 1rem', background: 'var(--room-accent-glow, rgba(0,204,102,0.08))',
        borderBottom: '1px solid var(--room-border, var(--border-primary))',
        display: 'flex', alignItems: 'center', gap: '0.75rem',
      }}>
        <span style={{
          width: 8, height: 8, borderRadius: '50%', background: 'var(--room-accent, var(--accent-primary))',
          boxShadow: '0 0 8px var(--room-accent, var(--accent-primary))',
        }} />
        <span style={{ color: 'var(--room-accent, var(--accent-primary))', fontFamily: 'var(--font-mono)', fontSize: '11px', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          {ROOM_LABELS.day}
        </span>
        <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
          {agents.filter(a => a.room === 'day_trading').length} agents
        </span>
      </div>
      <WarroomPhaserGame room="day_trading" map="day-trading-room" onAgentClick={handleAgentClick} />
      <Link
        to="/editor/room/day_trading"
        style={{
          position: 'absolute', bottom: '1rem', right: '1rem', zIndex: 10,
          padding: '0.4rem 0.8rem', background: 'var(--bg-tertiary)', border: '1px solid var(--room-border, var(--border-primary))',
          borderRadius: 'var(--radius-sm)', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '0.7rem', textDecoration: 'none',
        }}
      >
        Customize Office
      </Link>
      <AgentInspector agent={selectedAgent} onClose={() => selectAgent(null)} />
    </div>
  );
}
