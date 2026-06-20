import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { analyticsApi, backtestApi } from '../utils/api-client';

const useAnalyticsStore = create(
  devtools(
    (set, get) => ({
      portfolio: null,
      equityCurve: [],
      leaderboard: [],
      leaderboardSort: 'return',
      correlation: {},
      attribution: null,
      backtestRunId: null,
      backtestStatus: null,   // 'running' | 'done' | 'failed' | null
      backtestResult: null,
      backtestHistory: [],
      loading: false,
      error: null,

      fetchPortfolio: async () => {
        try {
          const data = await analyticsApi.portfolio();
          set({ portfolio: data });
        } catch (err) {
          set({ error: err.message });
        }
      },

      fetchEquityCurve: async (days = 30, agentId = null) => {
        set({ loading: true });
        try {
          const data = await analyticsApi.equityCurve(days, agentId);
          set({ equityCurve: data, loading: false });
        } catch (err) {
          set({ loading: false, error: err.message });
        }
      },

      fetchLeaderboard: async (sortBy = 'return') => {
        set({ leaderboardSort: sortBy });
        try {
          const data = await analyticsApi.leaderboard(sortBy);
          set({ leaderboard: data });
        } catch (err) {
          set({ error: err.message });
        }
      },

      fetchCorrelation: async () => {
        try {
          const data = await analyticsApi.correlation();
          set({ correlation: data });
        } catch (err) {
          set({ error: err.message });
        }
      },

      fetchAttribution: async (dateStr = null) => {
        try {
          const data = await analyticsApi.attribution(dateStr);
          set({ attribution: data });
        } catch (err) {
          set({ error: err.message });
        }
      },

      runBacktest: async (payload) => {
        set({ backtestRunId: null, backtestStatus: 'running', backtestResult: null });
        try {
          const { run_id } = await backtestApi.run(payload);
          set({ backtestRunId: run_id });
          get()._pollBacktest(run_id);
        } catch (err) {
          set({ backtestStatus: 'failed', error: err.message });
        }
      },

      _pollBacktest: async (runId) => {
        const poll = async () => {
          try {
            const data = await backtestApi.poll(runId);
            if (data.status === 'running') {
              setTimeout(poll, 2000);
            } else {
              set({ backtestStatus: data.status, backtestResult: data.result_json });
            }
          } catch (err) {
            set({ backtestStatus: 'failed', error: err.message });
          }
        };
        poll();
      },

      fetchBacktestHistory: async (agentId = null) => {
        try {
          const data = await backtestApi.history(agentId);
          set({ backtestHistory: data });
        } catch (err) {
          set({ error: err.message });
        }
      },
    }),
    { name: 'analytics-store' }
  )
);

export default useAnalyticsStore;
