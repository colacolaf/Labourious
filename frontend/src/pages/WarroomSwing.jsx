import { useCallback } from 'react';
import WarroomPhaserGame from '../components/Warroom/WarroomPhaserGame';
import AgentInspector from '../components/Warroom/AgentInspector';
import useAgentsStore from '../stores/agents.store';

export default function WarroomSwing() {
  const agents = useAgentsStore((s) => s.agents);
  const selectedAgent = useAgentsStore((s) => s.selectedAgent);
  const selectAgent = useAgentsStore((s) => s.selectAgent);

  const handleAgentClick = useCallback(({ agentId } = {}) => {
    const agent = agents.find((a) => a.id === agentId);
    if (agent) selectAgent(agent);
  }, [agents, selectAgent]);

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <WarroomPhaserGame room="swing_trading" map="sector-room" onAgentClick={handleAgentClick} />
      <AgentInspector agent={selectedAgent} onClose={() => selectAgent(null)} />
    </div>
  );
}
