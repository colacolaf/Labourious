import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { authApi } from '../utils/api-client';

const LS_ACCESS = 'auth_access_token';
const LS_REFRESH = 'auth_refresh_token';

const useAuthStore = create(devtools((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  get isLoggedIn() { return !!get().accessToken; },

  loadFromStorage: () => {
    const accessToken = localStorage.getItem(LS_ACCESS);
    const refreshToken = localStorage.getItem(LS_REFRESH);
    if (accessToken) set({ accessToken, refreshToken });
  },

  login: async (email, password) => {
    const data = await authApi.login({ email, password });
    localStorage.setItem(LS_ACCESS, data.access_token);
    localStorage.setItem(LS_REFRESH, data.refresh_token);
    set({ accessToken: data.access_token, refreshToken: data.refresh_token });
    try {
      const user = await authApi.me();
      set({ user });
    } catch (_) {}
    return data;
  },

  logout: () => {
    localStorage.removeItem(LS_ACCESS);
    localStorage.removeItem(LS_REFRESH);
    set({ user: null, accessToken: null, refreshToken: null });
  },

  refreshTokens: async () => {
    const { refreshToken } = get();
    const data = await authApi.refresh({ refresh_token: refreshToken });
    localStorage.setItem(LS_ACCESS, data.access_token);
    if (data.refresh_token) localStorage.setItem(LS_REFRESH, data.refresh_token);
    set({ accessToken: data.access_token });
    return data;
  },
}), { name: 'auth-store' }));

export default useAuthStore;
