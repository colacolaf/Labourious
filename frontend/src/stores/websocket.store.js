import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export const useWebSocketStore = create(
  devtools(
    (set) => ({
      isConnected: false,
      lastMessage: null,
      reconnectCount: 0,

      setConnected: (connected) => set({ isConnected: connected }),
      setLastMessage: (message) => set({ lastMessage: message }),
      incrementReconnect: () =>
        set((state) => ({ reconnectCount: state.reconnectCount + 1 })),
      resetReconnect: () => set({ reconnectCount: 0 }),
    }),
    { name: 'websocket-store' }
  )
);
