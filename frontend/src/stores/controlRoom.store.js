import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { brokersApi, llmApi, agentsApi, settingsApi } from '../utils/api-client';

const useControlRoomStore = create(devtools((set, get) => ({
  brokers: [],
  availableBrokers: [],
  llmConfig: null,
  agents: [],
  settings: null,
  loading: false,
  error: null,
  saving: false,

  fetchBrokers: async () => {
    set({ loading: true, error: null });
    try {
      const [list, avail] = await Promise.all([brokersApi.list(), brokersApi.available()]);
      set({ brokers: list, availableBrokers: avail.brokers ?? [], loading: false });
    } catch (err) {
      set({ loading: false, error: err.message });
    }
  },

  fetchLLM: async () => {
    set({ loading: true, error: null });
    try {
      const data = await llmApi.getConfig();
      set({ llmConfig: data, loading: false });
    } catch (err) {
      set({ loading: false, error: err.message });
    }
  },

  fetchAgents: async () => {
    set({ loading: true, error: null });
    try {
      const data = await agentsApi.list();
      set({ agents: Array.isArray(data) ? data : data?.items ?? [], loading: false });
    } catch (err) {
      set({ loading: false, error: err.message });
    }
  },

  fetchSettings: async () => {
    set({ loading: true, error: null });
    try {
      const data = await settingsApi.get();
      set({ settings: data, loading: false });
    } catch (err) {
      set({ loading: false, error: err.message });
    }
  },

  fetchAll: async () => {
    const { fetchBrokers, fetchLLM, fetchAgents, fetchSettings } = get();
    await Promise.allSettled([fetchBrokers(), fetchLLM(), fetchAgents(), fetchSettings()]);
  },

  connectBroker: async (data) => {
    set({ saving: true, error: null });
    try {
      const broker = await brokersApi.connect(data);
      set((s) => ({
        brokers: s.brokers.some((b) => b.broker_name === broker.broker_name)
          ? s.brokers.map((b) => b.broker_name === broker.broker_name ? broker : b)
          : [...s.brokers, broker],
        saving: false,
      }));
    } catch (err) {
      set({ saving: false, error: err.message });
      throw err;
    }
  },

  testBroker: async (name) => {
    try {
      return await brokersApi.test(name);
    } catch (err) {
      return { connected: false, message: err.message };
    }
  },

  patchLLM: async (data) => {
    set({ saving: true, error: null });
    try {
      const updated = await llmApi.patchConfig(data);
      set({ llmConfig: { ...get().llmConfig, ...updated }, saving: false });
    } catch (err) {
      set({ saving: false, error: err.message });
      throw err;
    }
  },

  testLLM: async () => {
    try {
      return await llmApi.test();
    } catch (err) {
      return { ok: false, latency_ms: 0, error: err.message };
    }
  },

  startAgent: async (id) => {
    try {
      const updated = await agentsApi.start(id);
      set((s) => ({ agents: s.agents.map((a) => a.id === id ? { ...a, ...updated } : a) }));
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  stopAgent: async (id) => {
    try {
      const updated = await agentsApi.stop(id);
      set((s) => ({ agents: s.agents.map((a) => a.id === id ? { ...a, ...updated } : a) }));
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  pauseAgent: async (id) => {
    try {
      const updated = await agentsApi.pause(id);
      set((s) => ({ agents: s.agents.map((a) => a.id === id ? { ...a, ...updated } : a) }));
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  saveAllocation: async (data) => {
    set({ saving: true, error: null });
    try {
      await settingsApi.patchAllocation(data);
      set((s) => ({ settings: { ...s.settings, allocation: { ...s.settings?.allocation, ...data } }, saving: false }));
    } catch (err) {
      set({ saving: false, error: err.message });
      throw err;
    }
  },

  changePassword: async (data) => {
    set({ saving: true, error: null });
    try {
      const res = await settingsApi.changePassword(data);
      set({ saving: false });
      return res;
    } catch (err) {
      set({ saving: false, error: err.message });
      throw err;
    }
  },

  clearError: () => set({ error: null }),
}), { name: 'control-room-store' }));

export default useControlRoomStore;
