import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { analyticsApi, healthApi, tradesApi } from '../utils/api-client';

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
        sharpeRatio: null,
        maxDrawdown: null,
        return30d: null,
      },
      portfolioHistory: [],
      recentTrades: [],
      performanceByAgent: {},

      backendStatus: 'unknown',
      backendVersion: null,
      backendUptime: null,
      dbStatus: 'unknown',
      vaultStatus: 'unknown',
      llmStatus: 'unknown',
      _refreshInterval: null,

      loading: false,
      portfolioLoading: false,
      error: null,
      lastFetched: null,

      fetchPortfolioSummary: async () => {
        set({ portfolioLoading: true, error: null });
        try {
          const data = await analyticsApi.portfolio();
          set({
            portfolio: {
              totalValue: data.total_pnl ?? 0,
              cashBalance: 0,
              unrealizedPnl: 0,
              realizedPnl: data.total_pnl ?? 0,
              totalPnl: data.total_pnl ?? 0,
              totalPnlPct: data.return_30d_pct ?? 0,
              activeAgents: data.agent_count ?? 0,
              totalTrades: data.total_trades ?? 0,
              winRate: data.win_rate ?? 0,
              sharpeRatio: data.sharpe_ratio ?? null,
              maxDrawdown: data.max_drawdown ?? null,
              return30d: data.return_30d_pct ?? null,
            },
            portfolioLoading: false,
            lastFetched: Date.now(),
          });
        } catch (err) {
          set({ portfolioLoading: false, error: err.message });
        }
      },

      fetchPortfolioHistory: async (days = 30) => {
        try {
          const data = await analyticsApi.equityCurve(days);
          set({ portfolioHistory: Array.isArray(data) ? data : [] });
        } catch (err) {
          set({ error: err.message });
        }
      },

      startAutoRefresh: (intervalMs = 30_000) => {
        const { _refreshInterval } = get();
        if (_refreshInterval) return;
        const id = setInterval(() => {
          get().fetchPortfolioSummary();
          get().fetchPortfolioHistory();
        }, intervalMs);
        set({ _refreshInterval: id });
      },

      stopAutoRefresh: () => {
        const { _refreshInterval } = get();
        if (_refreshInterval) {
          clearInterval(_refreshInterval);
          set({ _refreshInterval: null });
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

      fetchRecentTrades: async (limit = 20) => {
        try {
          const data = await tradesApi.list({ limit });
          set({ recentTrades: Array.isArray(data) ? data : [] });
        } catch (err) {
          set({ error: err.message });
        }
      },

      fetchSystemHealth: async () => {
        try {
          const data = await healthApi.full();
          set({
            backendStatus: data.backend === 'ok' ? 'connected' : 'degraded',
            backendVersion: data.version ?? null,
            backendUptime: data.uptime_seconds,
            dbStatus: data.db === 'ok' ? 'ok' : 'error',
            vaultStatus: data.vault,
            llmStatus: data.llm,
          });
        } catch {
          set({ backendStatus: 'disconnected', dbStatus: 'error' });
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
