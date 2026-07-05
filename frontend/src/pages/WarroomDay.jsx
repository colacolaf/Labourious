import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import WarroomPhaserGame from '../components/Warroom/WarroomPhaserGame';
import AgentInspector from '../components/Warroom/AgentInspector';
import useAgentsStore from '../stores/agents.store';

export default function WarroomDay() {
  const agents = useAgentsStore((s) => s.agents);
  const selectedAgent = useAgentsStore((s) => s.selectedAgent);
  const selectAgent = useAgentsStore((s) => s.selectAgent);

  const handleAgentClick = useCallback(({ agentId } = {}) => {
    const agent = agents.find((a) => a.id === agentId);
    if (agent) selectAgent(agent);
  }, [agents, selectAgent]);

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <WarroomPhaserGame room="day_trading" map="day-trading-room" onAgentClick={handleAgentClick} />
      <Link
        to="/editor/room/day_trading"
        style={{
          position: 'absolute', top: 'var(--space-3)', right: 'var(--space-3)', zIndex: 10,
          padding: '0.4rem 0.8rem', background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)',
          borderRadius: 4, color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', textDecoration: 'none',
        }}
      >
        Customize Office
      </Link>
      <AgentInspector agent={selectedAgent} onClose={() => selectAgent(null)} />
    </div>
  );
}
