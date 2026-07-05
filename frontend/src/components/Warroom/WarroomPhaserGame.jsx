import { useLayoutEffect, useEffect, useRef } from 'react';
import { createGame } from '../../game/main';
import { EventBus } from '../../game/EventBus';

let instanceCounter = 0;

export default function WarroomPhaserGame({ room, map, onAgentClick }) {
  const gameRef = useRef(null);
  const containerIdRef = useRef(`warroom-phaser-game-${instanceCounter++}`);

  // Guard against React StrictMode's double-invoke: only create a game if one
  // isn't already tracked in the ref, and always tear it down on cleanup.
  useLayoutEffect(() => {
    if (gameRef.current === null) {
      gameRef.current = createGame(containerIdRef.current);
    }
    return () => {
      gameRef.current?.destroy(true);
      gameRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!onAgentClick) return undefined;
    EventBus.on('agent-clicked', onAgentClick);
    return () => EventBus.off('agent-clicked', onAgentClick);
  }, [onAgentClick]);

  return <div id={containerIdRef.current} data-room={room} data-map={map} />;
}
