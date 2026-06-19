import { renderHook } from "@testing-library/react";
import { useWebSocket } from "../../components/Warroom/../../../hooks/useWebSocket";

// Mock WebSocket global
class MockWebSocket {
  constructor() { this.readyState = 1; }
  send() {}
  close() {}
}
global.WebSocket = MockWebSocket;

// Mock stores used by the hook
jest.mock("../../stores/websocket.store", () => ({
  useWebSocketStore: () => ({
    setConnected: jest.fn(),
    setLastMessage: jest.fn(),
    incrementReconnect: jest.fn(),
    resetReconnect: jest.fn(),
  }),
}));
jest.mock("../../stores/agents.store", () => ({ getState: () => ({ updateAgentLocally: jest.fn() }) }));
jest.mock("../../stores/trades.store", () => ({ useTradesStore: { getState: () => ({ addTrade: jest.fn() }) } }));
jest.mock("../../stores/ui.store", () => ({ useUIStore: { getState: () => ({ setPendingApproval: jest.fn(), addToast: jest.fn() }) } }));
jest.mock("../../stores/dashboard.store", () => ({ getState: () => ({ updatePortfolioLocally: jest.fn() }) }));
jest.mock("../../utils/constants", () => ({ WS_BASE_URL: "ws://localhost:8000" }));

test("returns send and approveTrade functions", () => {
  const { result } = renderHook(() => useWebSocket());
  expect(typeof result.current.send).toBe("function");
  expect(typeof result.current.approveTrade).toBe("function");
});
