import { useState, useCallback, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import IsometricGrid, { toScreen, TILE_W } from './IsometricGrid';
import AgentSprite from './AgentSprite';
import AgentInspector from './AgentInspector';
import TradeNotification from './TradeNotification';
import ApprovalDialog from './ApprovalDialog';
import useAgentsStore from '../../stores/agents.store';
import { useWebSocketStore } from '../../stores/websocket.store';
import { useWebSocket } from '../../hooks/useWebSocket';

export default function Warroom({ room }) {
  const { agents, selectAgent, selectedAgent, startPolling, stopPolling } = useAgentsStore();
  const { lastMessage } = useWebSocketStore();
  const { approveTrade } = useWebSocket();

  const [notifications, setNotifications] = useState([]); // [{id, trade, svgX, svgY}]
  const [approvalQueue, setApprovalQueue] = useState([]);
  const currentApproval = approvalQueue[0] ?? null;

  // Start polling on mount, stop on unmount
  useEffect(() => {
    startPolling();
    return () => stopPolling();
  }, [startPolling, stopPolling]);

  // Filter agents for this room
  const roomAgents = room ? agents.filter((a) => a.room === room) : agents;

  // Handle inbound WS messages
  useEffect(() => {
    if (!lastMessage) return;
    const msg = lastMessage;

    if (msg.event === 'trade_executed' || msg.type === 'trade_executed') {
      const agent = agents.find((a) => a.id === msg.agent_id || a.id === String(msg.agent_id));
      if (agent) {
        const { x, y } = toScreen(agent.grid_col ?? 0, agent.grid_row ?? 0);
        const notif = {
          id: `${Date.now()}-${msg.agent_id}`,
          trade: { symbol: msg.symbol, action: msg.action, pnl: msg.pnl },
          svgX: x + TILE_W / 2,
          svgY: y,
        };
        setNotifications((prev) => [...prev, notif]);
      }
    }

    if (msg.event === 'trade_approval_required' || msg.type === 'agent_approval_needed') {
      const agent = agents.find((a) => a.id === msg.agent_id || a.id === String(msg.agent_id));
      const approval = { ...msg, agent_name: msg.agent_name ?? agent?.name };
      setApprovalQueue((prev) => [...prev, approval]);
    }

    if (msg.event === 'agent_update' || msg.event === 'agent_paused' || msg.event === 'bodyguard_pause_all') {
      if (msg.agent_id) {
        useAgentsStore.getState().updateAgentLocally(msg.agent_id, {
          status: msg.status,
          confidence_score: msg.confidence_score,
        });
      }
    }
  }, [lastMessage, agents]);

  const removeNotification = useCallback((id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const handleDecide = useCallback((tradeId, approved) => {
    approveTrade(tradeId, approved);
    setApprovalQueue((prev) => prev.filter((a) => a.trade_id !== tradeId));
  }, [approveTrade]);

  const handleAgentClick = useCallback((agent) => {
    selectAgent(selectedAgent?.id === agent.id ? null : agent);
  }, [selectAgent, selectedAgent]);

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <IsometricGrid>
        {/* Agent sprites */}
        {roomAgents.map((agent) => (
          <AgentSprite
            key={agent.id}
            agent={agent}
            onClick={handleAgentClick}
          />
        ))}

        {/* Trade notifications (SVG-space) */}
        <AnimatePresence>
          {notifications.map((n) => (
            <TradeNotification
              key={n.id}
              trade={n.trade}
              svgX={n.svgX}
              svgY={n.svgY}
              onDone={() => removeNotification(n.id)}
            />
          ))}
        </AnimatePresence>
      </IsometricGrid>

      {/* Inspector (DOM-space, overlays grid) */}
      <AgentInspector
        agent={selectedAgent}
        onClose={() => selectAgent(null)}
      />

      {/* Approval dialog */}
      <ApprovalDialog approval={currentApproval} onDecide={handleDecide} />
    </div>
  );
}
