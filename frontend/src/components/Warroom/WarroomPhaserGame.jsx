import { useLayoutEffect, useEffect, useRef, useId, useState } from 'react';
import { createGame } from '../../game/main';
import { EventBus } from '../../game/EventBus';
import { useWarroomAgents } from './hooks/useWarroomAgents';

export default function WarroomPhaserGame({ room, map, onAgentClick }) {
  const gameRef = useRef(null);
  const containerId = `warroom-phaser-game-${useId()}`;
  // Populated once WarroomScene finishes spawning TradingAgent instances (see 'agents-spawned'
  // below) — starts empty since Phaser scene creation is async relative to this component mounting.
  const [agentSprites, setAgentSprites] = useState([]);

  // Guard against React StrictMode's double-invoke: only create a game if one
  // isn't already tracked in the ref, and always tear it down on cleanup.
  useLayoutEffect(() => {
    if (gameRef.current === null) {
      gameRef.current = createGame(containerId, map, room);
    }
    return () => {
      gameRef.current?.destroy(true);
      gameRef.current = null;
    };
  }, [containerId, map, room]);

  useEffect(() => {
    const handleAgentsSpawned = (sprites) => setAgentSprites(Array.isArray(sprites) ? sprites : []);
    EventBus.on('agents-spawned', handleAgentsSpawned);
    return () => EventBus.off('agents-spawned', handleAgentsSpawned);
  }, []);

  useEffect(() => {
    if (!onAgentClick) return undefined;
    EventBus.on('agent-clicked', onAgentClick);
    return () => EventBus.off('agent-clicked', onAgentClick);
  }, [onAgentClick]);

  // Owns the WS-event -> sprite-method wiring for this room's TradingAgent instances.
  useWarroomAgents(room, agentSprites);

  return <div id={containerId} data-room={room} data-map={map} />;
}
