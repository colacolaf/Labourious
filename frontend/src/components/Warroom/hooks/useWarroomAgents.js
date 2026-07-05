import { useEffect, useRef } from 'react';
import { agentsApi } from '../../../utils/api-client';
import { useWebSocketStore } from '../../../stores/websocket.store';
import useAgentsStore from '../../../stores/agents.store';

// `agentSprites` is a plain array of TradingAgent instances (see ../sprites/TradingAgent.js),
// owned by WarroomScene and handed up to React via the 'agents-spawned' EventBus event
// (see WarroomPhaserGame.jsx). It starts empty — Phaser scene creation is async — and gets
// replaced with the populated array once, which re-triggers the effects below via the
// [room, agentSprites] / [agents, agentSprites] deps. No changes needed here for that: the
// effects already re-run whenever the `agentSprites` array reference changes.
export function useWarroomAgents(room, agentSprites) {
  const lastMessage = useWebSocketStore((s) => s.lastMessage);
  const agents = useAgentsStore((s) => s.agents);
  const demoTimer = useRef(null);
  const hasRealEvent = useRef(false);

  // On mount: assign IDs and apply initial confidence/paused state
  useEffect(() => {
    agentsApi.list({ room }).then((fetched) => {
      if (!Array.isArray(fetched)) return;
      fetched.forEach((agent, i) => {
        const sprite = agentSprites[i];
        if (!sprite) return;
        sprite.id = agent.id;
        if (sprite.setConfidence) sprite.setConfidence(agent.confidence_score ?? 50);
        if (sprite.setPaused) sprite.setPaused(agent.status === 'paused');
      });
    }).catch(() => {});
  }, [room, agentSprites]);

  // Re-sync sprites when agents store updates (polling or WS)
  useEffect(() => {
    agents.forEach((agent) => {
      const sprite = agentSprites.find((s) => s && s.id === agent.id);
      if (!sprite) return;
      if (sprite.setConfidence) sprite.setConfidence(agent.confidence_score ?? 50);
      if (sprite.setPaused) sprite.setPaused(agent.status === 'paused');
    });
  }, [agents, agentSprites]);

  useEffect(() => {
    demoTimer.current = setTimeout(() => {
      if (!hasRealEvent.current) window.__LABOURIOUS_DEMO__ = true;
    }, 3000);
    return () => clearTimeout(demoTimer.current);
  }, []);

  useEffect(() => {
    if (!lastMessage) return;
    const msg = lastMessage;
    const key = msg.event ?? msg.type;

    if (key === 'trade_executed' && msg.agent_id) {
      hasRealEvent.current = true;
      window.__LABOURIOUS_DEMO__ = false;
      const sprite = agentSprites.find((s) => s && s.id === msg.agent_id);
      if (sprite) {
        sprite.onTrade(msg.symbol ?? 'TRADE', msg.action ?? 'BUY', msg.pnl ?? 0);
        if (sprite.setConfidence) sprite.setConfidence(msg.confidence_score ?? 50);
      }
    }

    if ((key === 'agent_update' || key === 'agent_paused') && msg.agent_id) {
      hasRealEvent.current = true;
      const sprite = agentSprites.find((s) => s && s.id === msg.agent_id);
      if (sprite) {
        if (msg.status === 'running' || msg.data?.status === 'processing') sprite.onProcessing();
        if (sprite.setPaused) sprite.setPaused(msg.status === 'paused' || msg.data?.status === 'paused');
        if (sprite.setConfidence && msg.confidence_score != null) sprite.setConfidence(msg.confidence_score);
      }
    }

    if (key === 'bodyguard_pause_all') {
      agentSprites.forEach((sprite) => { if (sprite?.setPaused) sprite.setPaused(true); });
    }
  }, [lastMessage, agentSprites]);
}
