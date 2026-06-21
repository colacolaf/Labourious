import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { notificationsApi } from '../utils/api-client';

const useNotificationsStore = create(devtools((set) => ({
  preferences: null,
  loading: false,
  error: null,
  saving: false,

  fetchPreferences: async () => {
    set({ loading: true, error: null });
    try {
      const data = await notificationsApi.getPreferences();
      set({ preferences: data, loading: false });
    } catch (err) {
      set({ loading: false, error: err.message });
    }
  },

  updatePreferences: async (patch) => {
    set({ saving: true, error: null });
    try {
      const data = await notificationsApi.updatePreferences(patch);
      set({ preferences: data, saving: false });
      return data;
    } catch (err) {
      set({ saving: false, error: err.message });
      throw err;
    }
  },
}), { name: 'notifications-store' }));

export default useNotificationsStore;
