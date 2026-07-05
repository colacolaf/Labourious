import { useCallback } from 'react';
import WarroomPhaserGame from '../components/Warroom/WarroomPhaserGame';
import AgentInspector from '../components/Warroom/AgentInspector';
import useAgentsStore from '../stores/agents.store';

export default function WarroomLongTerm() {
  const agents = useAgentsStore((s) => s.agents);
  const selectedAgent = useAgentsStore((s) => s.selectedAgent);
  const selectAgent = useAgentsStore((s) => s.selectAgent);

  // Phaser only knows the clicked agent's id — look up the full object the store already
  // has (App.jsx polls agents.store globally) before handing it to AgentInspector.
  const handleAgentClick = useCallback(({ agentId } = {}) => {
    const agent = agents.find((a) => a.id === agentId);
    if (agent) selectAgent(agent);
  }, [agents, selectAgent]);

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <WarroomPhaserGame room="long_term" map="investment-room" onAgentClick={handleAgentClick} />
      <AgentInspector agent={selectedAgent} onClose={() => selectAgent(null)} />
    </div>
  );
}
