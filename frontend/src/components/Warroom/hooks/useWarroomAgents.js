import { useEffect, useRef } from 'react';
import { agentsApi } from '../../../utils/api-client';
import { useWebSocketStore } from '../../../stores/websocket.store';

export function useWarroomAgents(room, agentSprites) {
  const lastMessage = useWebSocketStore((s) => s.lastMessage);
  const demoTimer = useRef(null);
  const hasRealEvent = useRef(false);

  useEffect(() => {
    agentsApi.list({ room }).then((agents) => {
      if (!Array.isArray(agents)) return;
      agents.forEach((agent, i) => {
        if (agentSprites[i]) agentSprites[i].id = agent.id;
      });
    }).catch(() => {});
  }, [room, agentSprites]);

  useEffect(() => {
    demoTimer.current = setTimeout(() => {
      if (!hasRealEvent.current) window.__LABOURIOUS_DEMO__ = true;
    }, 3000);
    return () => clearTimeout(demoTimer.current);
  }, []);

  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === 'trade_executed' && lastMessage.agent_id) {
      hasRealEvent.current = true;
      window.__LABOURIOUS_DEMO__ = false;
      const sprite = agentSprites.find((s) => s && s.id === lastMessage.agent_id);
      if (sprite) {
        sprite.onTrade(
          lastMessage.trade?.symbol ?? 'TRADE',
          lastMessage.trade?.action ?? 'BUY',
          lastMessage.trade?.pnl ?? 0
        );
      }
    }

    if (lastMessage.type === 'agent_update' && lastMessage.agent_id) {
      if (lastMessage.data?.status === 'processing') {
        hasRealEvent.current = true;
        const sprite = agentSprites.find((s) => s && s.id === lastMessage.agent_id);
        if (sprite) sprite.onProcessing();
      }
    }
  }, [lastMessage, agentSprites]);
}
