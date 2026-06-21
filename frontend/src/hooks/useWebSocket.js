import { useEffect, useRef, useCallback } from 'react';
import { useWebSocketStore } from '../stores/websocket.store';
import useAgentsStore from '../stores/agents.store';
import { useTradesStore } from '../stores/trades.store';
import { useUIStore } from '../stores/ui.store';
import useDashboardStore from '../stores/dashboard.store';
import { WS_BASE_URL } from '../utils/constants';

const BACKOFF_STEPS = [1000, 2000, 5000, 10000, 30000]; // ms

export function useWebSocket(path = '/ws/connect') {
  // ponytail: path matches backend @router.websocket("/connect") with prefix "/ws"
  const ws = useRef(null);
  const retryTimer = useRef(null);
  const retryCount = useRef(0);

  const { setConnected, setLastMessage, incrementReconnect, resetReconnect } = useWebSocketStore();

  // Dispatch inbound messages to the right store
  const dispatch = useCallback((msg) => {
    setLastMessage(msg);
    const key = msg.event ?? msg.type;

    switch (key) {
      case 'agent_update':
      case 'agent_paused':
        if (msg.agent_id) {
          useAgentsStore.getState().updateAgentLocally(msg.agent_id, msg.data ?? {
            status: msg.status,
            confidence_score: msg.confidence_score,
          });
        }
        break;
      case 'trade_executed':
        if (msg.trade) useTradesStore.getState().addTrade(msg.trade);
        break;
      case 'trade_approval_required':
      case 'agent_approval_needed':
        useUIStore.getState().setPendingApproval(msg);
        break;
      case 'portfolio_update':
        useDashboardStore.getState().updatePortfolioLocally(msg.data ?? {});
        break;
      case 'risk_alert':
      case 'bodyguard_pause_all':
        useUIStore.getState().addToast({ type: 'error', message: msg.message ?? msg.reason ?? 'Risk alert' });
        break;
      default:
        break;
    }
  }, [setLastMessage]);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    ws.current = new WebSocket(`${WS_BASE_URL}${path}`);

    ws.current.onopen = () => {
      setConnected(true);
      resetReconnect();
      retryCount.current = 0;
    };

    ws.current.onmessage = (event) => {
      try {
        dispatch(JSON.parse(event.data));
      } catch {
        setLastMessage(event.data);
      }
    };

    ws.current.onclose = () => {
      setConnected(false);
      incrementReconnect();
      const delay = BACKOFF_STEPS[Math.min(retryCount.current, BACKOFF_STEPS.length - 1)];
      retryCount.current += 1;
      retryTimer.current = setTimeout(connect, delay);
    };

    ws.current.onerror = () => {
      setConnected(false);
    };
  }, [path, setConnected, setLastMessage, incrementReconnect, resetReconnect, dispatch]);

  const send = useCallback((data) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  }, []);

  const approveTrade = useCallback((tradeId, approved) => {
    send({ type: 'approve_trade', trade_id: tradeId, approved });
  }, [send]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(retryTimer.current);
      ws.current?.close();
    };
  }, [connect]);

  return { send, approveTrade };
}
