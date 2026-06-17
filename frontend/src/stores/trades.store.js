import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { tradesApi } from '../utils/api-client';

export const useTradesStore = create(
  devtools(
    (set) => ({
      trades: [],
      loading: false,
      error: null,

      setTrades: (trades) => set({ trades }),

      addTrade: (trade) =>
        set((state) => ({ trades: [trade, ...state.trades] })),

      fetchTrades: async (params) => {
        set({ loading: true, error: null });
        try {
          const data = await tradesApi.list(params);
          set({
            trades: Array.isArray(data) ? data : data?.items ?? [],
            loading: false,
          });
        } catch (err) {
          set({ loading: false, error: err.message });
        }
      },

      clearError: () => set({ error: null }),
    }),
    { name: 'trades-store' }
  )
);
