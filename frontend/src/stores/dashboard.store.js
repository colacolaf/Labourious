import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { performanceApi, healthApi } from '../utils/api-client';

const useDashboardStore = create(
  devtools(
    (set, get) => ({
      portfolio: {
        totalValue: 0,
        cashBalance: 0,
        unrealizedPnl: 0,
        realizedPnl: 0,
        totalPnl: 0,
        totalPnlPct: 0,
        activeAgents: 0,
        totalTrades: 0,
        winRate: 0,
      },
      portfolioHistory: [],
      recentTrades: [],
      performanceByAgent: {},

      backendStatus: 'unknown',
      backendVersion: null,
      backendUptime: null,

      loading: false,
      portfolioLoading: false,
      error: null,
      lastFetched: null,

      fetchPortfolioSummary: async () => {
        set({ portfolioLoading: true, error: null });
        try {
          const data = await performanceApi.summary();
          set({
            portfolio: {
              totalValue: data.total_value ?? 0,
              cashBalance: data.cash_balance ?? 0,
              unrealizedPnl: data.unrealized_pnl ?? 0,
              realizedPnl: data.realized_pnl ?? 0,
              totalPnl: data.total_pnl ?? 0,
              totalPnlPct: data.total_pnl_pct ?? 0,
              activeAgents: data.active_agents ?? 0,
              totalTrades: data.total_trades ?? 0,
              winRate: data.win_rate ?? 0,
            },
            portfolioLoading: false,
            lastFetched: Date.now(),
          });
        } catch (err) {
          set({ portfolioLoading: false, error: err.message });
        }
      },

      fetchPortfolioHistory: async (params) => {
        try {
          const data = await performanceApi.portfolio(params);
          set({ portfolioHistory: Array.isArray(data) ? data : data?.items ?? [] });
        } catch (err) {
          set({ error: err.message });
        }
      },

      checkBackendHealth: async () => {
        try {
          const data = await healthApi.check();
          set({
            backendStatus: data.status === 'ok' ? 'connected' : 'degraded',
            backendVersion: data.version,
            backendUptime: data.uptime_seconds,
          });
        } catch {
          set({ backendStatus: 'disconnected' });
        }
      },

      setRecentTrades: (trades) => set({ recentTrades: trades }),

      updatePortfolioLocally: (patch) => {
        set((state) => ({
          portfolio: { ...state.portfolio, ...patch },
        }));
      },

      appendPortfolioHistory: (point) => {
        set((state) => ({
          portfolioHistory: [...state.portfolioHistory.slice(-499), point],
        }));
      },

      clearError: () => set({ error: null }),

      isConnected: () => get().backendStatus === 'connected',
    }),
    { name: 'dashboard-store' }
  )
);

export default useDashboardStore;
