import { useLayoutEffect, useEffect, useRef, useId } from 'react';
import { createGame } from '../../game/main';
import { EventBus } from '../../game/EventBus';

export default function WarroomPhaserGame({ room, map, onAgentClick }) {
  const gameRef = useRef(null);
  const containerId = `warroom-phaser-game-${useId()}`;

  // Guard against React StrictMode's double-invoke: only create a game if one
  // isn't already tracked in the ref, and always tear it down on cleanup.
  useLayoutEffect(() => {
    if (gameRef.current === null) {
      gameRef.current = createGame(containerId);
    }
    return () => {
      gameRef.current?.destroy(true);
      gameRef.current = null;
    };
  }, [containerId]);

  useEffect(() => {
    if (!onAgentClick) return undefined;
    EventBus.on('agent-clicked', onAgentClick);
    return () => EventBus.off('agent-clicked', onAgentClick);
  }, [onAgentClick]);

  return <div id={containerId} data-room={room} data-map={map} />;
}
