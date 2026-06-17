import { useEffect, useRef, useCallback } from 'react';
import { useWebSocketStore } from '../stores/websocket.store';
import { WS_BASE_URL } from '../utils/constants';

export function useWebSocket(path = '/ws/connect') {
  const ws = useRef(null);
  const { setConnected, setLastMessage, incrementReconnect } = useWebSocketStore();

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    ws.current = new WebSocket(`${WS_BASE_URL}${path}`);

    ws.current.onopen = () => setConnected(true);

    ws.current.onmessage = (event) => {
      try {
        setLastMessage(JSON.parse(event.data));
      } catch {
        setLastMessage(event.data);
      }
    };

    ws.current.onclose = () => {
      setConnected(false);
      incrementReconnect();
    };

    ws.current.onerror = () => {
      setConnected(false);
    };
  }, [path, setConnected, setLastMessage, incrementReconnect]);

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);

  return { connect };
}
