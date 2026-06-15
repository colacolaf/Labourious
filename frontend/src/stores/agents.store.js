import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { agentsApi } from '../utils/api-client';

const useAgentsStore = create(
  devtools(
    (set, get) => ({
      agents: [],
      selectedAgent: null,
      loading: false,
      error: null,
      lastFetched: null,

      fetchAgents: async () => {
        set({ loading: true, error: null });
        try {
          const data = await agentsApi.list();
          set({
            agents: Array.isArray(data) ? data : data?.items ?? [],
            loading: false,
            lastFetched: Date.now(),
          });
        } catch (err) {
          set({ loading: false, error: err.message });
        }
      },

      fetchAgent: async (id) => {
        set({ loading: true, error: null });
        try {
          const agent = await agentsApi.get(id);
          set((state) => ({
            agents: state.agents.some((a) => a.id === agent.id)
              ? state.agents.map((a) => (a.id === agent.id ? agent : a))
              : [...state.agents, agent],
            selectedAgent: agent,
            loading: false,
          }));
        } catch (err) {
          set({ loading: false, error: err.message });
        }
      },

      createAgent: async (data) => {
        set({ loading: true, error: null });
        try {
          const agent = await agentsApi.create(data);
          set((state) => ({
            agents: [...state.agents, agent],
            loading: false,
          }));
          return agent;
        } catch (err) {
          set({ loading: false, error: err.message });
          throw err;
        }
      },

      updateAgent: async (id, data) => {
        try {
          const updated = await agentsApi.update(id, data);
          set((state) => ({
            agents: state.agents.map((a) => (a.id === id ? updated : a)),
            selectedAgent: state.selectedAgent?.id === id ? updated : state.selectedAgent,
          }));
          return updated;
        } catch (err) {
          set({ error: err.message });
          throw err;
        }
      },

      deleteAgent: async (id) => {
        try {
          await agentsApi.delete(id);
          set((state) => ({
            agents: state.agents.filter((a) => a.id !== id),
            selectedAgent: state.selectedAgent?.id === id ? null : state.selectedAgent,
          }));
        } catch (err) {
          set({ error: err.message });
          throw err;
        }
      },

      startAgent: async (id) => {
        try {
          const updated = await agentsApi.start(id);
          set((state) => ({
            agents: state.agents.map((a) => (a.id === id ? { ...a, ...updated } : a)),
          }));
        } catch (err) {
          set({ error: err.message });
          throw err;
        }
      },

      stopAgent: async (id) => {
        try {
          const updated = await agentsApi.stop(id);
          set((state) => ({
            agents: state.agents.map((a) => (a.id === id ? { ...a, ...updated } : a)),
          }));
        } catch (err) {
          set({ error: err.message });
          throw err;
        }
      },

      pauseAgent: async (id) => {
        try {
          const updated = await agentsApi.pause(id);
          set((state) => ({
            agents: state.agents.map((a) => (a.id === id ? { ...a, ...updated } : a)),
          }));
        } catch (err) {
          set({ error: err.message });
          throw err;
        }
      },

      selectAgent: (agent) => set({ selectedAgent: agent }),

      updateAgentLocally: (id, patch) => {
        set((state) => ({
          agents: state.agents.map((a) => (a.id === id ? { ...a, ...patch } : a)),
          selectedAgent:
            state.selectedAgent?.id === id
              ? { ...state.selectedAgent, ...patch }
              : state.selectedAgent,
        }));
      },

      clearError: () => set({ error: null }),

      getAgentById: (id) => get().agents.find((a) => a.id === id),

      getRunningAgents: () => get().agents.filter((a) => a.status === 'running'),

      getTotalPnl: () =>
        get().agents.reduce((sum, a) => sum + (a.total_pnl ?? 0), 0),
    }),
    { name: 'agents-store' }
  )
);

export default useAgentsStore;
