import { useEffect, useRef } from 'react';
import { agentsApi } from '../../../utils/api-client';
import { useWebSocketStore } from '../../../stores/websocket.store';
import useAgentsStore from '../../../stores/agents.store';

// Demo-mode symbol lists, one per backend `room` — same three lists the deprecated Pixi
// PixiWarroom.jsx used (BLOOM_SYMBOLS/OAK_SYMBOLS/PIT_SYMBOLS), reused here rather than
// inventing a new list, keyed by the room-key mapping from the design spec.
const DEMO_SYMBOLS = {
  long_term: ['AAPL', 'MSFT', 'VOO', 'BRK.B', 'SPY', 'AMZN', 'JNJ'],
  swing_trading: ['TECH', 'UTIL', 'HLTH', 'ENRG', 'FINL', 'XLF', 'ROTATE'],
  day_trading: ['TSLA', 'NVDA', 'AMD', 'GME', 'SPY', 'QQQ', 'AAPL'],
};

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

  // Demo mode: no real WS events after 3s (see above) → fake occasional trades so the room
  // isn't static during a standalone demo. Lower priority than the core HeadBubble mechanics —
  // deliberately simple (random sprite, random symbol, random win/loss) rather than any real
  // scheduling/backend simulation.
  useEffect(() => {
    const symbols = DEMO_SYMBOLS[room] || DEMO_SYMBOLS.long_term;
    const interval = setInterval(() => {
      if (!window.__LABOURIOUS_DEMO__ || agentSprites.length === 0) return;
      const sprite = agentSprites[Math.floor(Math.random() * agentSprites.length)];
      if (!sprite?.onTrade) return;
      const symbol = symbols[Math.floor(Math.random() * symbols.length)];
      const win = Math.random() > 0.45;
      sprite.onTrade(symbol, win ? 'BUY' : 'SELL', win ? Math.random() * 500 : -Math.random() * 300);
    }, 2500);
    return () => clearInterval(interval);
  }, [room, agentSprites]);

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
        if (sprite.setConfidence) sprite.setConfidence(msg.confidence_score ?? 50, { showBubble: true });
      }
    }

    // Real backend event name is `trade_approval_required` (backend/trading/trade_executor.py)
    // — `agent_approval_needed` only ever existed in this codebase's dead/legacy WS dispatch
    // and is kept there for back-compat, not because the backend emits it.
    if (key === 'trade_approval_required' && msg.agent_id) {
      hasRealEvent.current = true;
      window.__LABOURIOUS_DEMO__ = false;
      const sprite = agentSprites.find((s) => s && s.id === msg.agent_id);
      if (sprite?.showApproval) {
        const timeoutSeconds = msg.expires_at
          ? Math.max(1, Math.round((new Date(msg.expires_at) - Date.now()) / 1000))
          : 30;
        sprite.showApproval(timeoutSeconds);
      }
    }

    if ((key === 'agent_update' || key === 'agent_paused') && msg.agent_id) {
      hasRealEvent.current = true;
      const sprite = agentSprites.find((s) => s && s.id === msg.agent_id);
      if (sprite) {
        if (msg.status === 'running' || msg.data?.status === 'processing') sprite.onProcessing();
        if (sprite.setPaused) {
          sprite.setPaused(msg.status === 'paused' || msg.data?.status === 'paused', msg.reason);
        }
        if (sprite.setConfidence && msg.confidence_score != null) {
          sprite.setConfidence(msg.confidence_score, { showBubble: true });
        }
      }
    }

    if (key === 'bodyguard_pause_all') {
      agentSprites.forEach((sprite) => { if (sprite?.setPaused) sprite.setPaused(true, msg.reason); });
    }
  }, [lastMessage, agentSprites]);
}
