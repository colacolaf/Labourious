import axios from 'axios';
import { API_BASE_URL } from './constants';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_access_token');
    if (token) config.headers['Authorization'] = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

let _isRefreshing = false;
let _refreshQueue = [];

apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const original = error.config;
    if (error?.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem('auth_refresh_token');
      if (!refreshToken) {
        // ponytail: lazy import avoids circular dep at module load time
        const { default: useAuthStore } = await import('../stores/auth.store');
        useAuthStore.getState().logout();
        return Promise.reject(error);
      }
      if (_isRefreshing) {
        return new Promise((resolve, reject) => {
          _refreshQueue.push({ resolve, reject });
        }).then((token) => {
          original.headers['Authorization'] = `Bearer ${token}`;
          return apiClient(original);
        });
      }
      _isRefreshing = true;
      try {
        const res = await apiClient.post('/api/auth/refresh', { refresh_token: refreshToken });
        const newToken = res.access_token ?? res.data?.access_token ?? res;
        localStorage.setItem('auth_access_token', typeof newToken === 'string' ? newToken : newToken.access_token);
        _refreshQueue.forEach(({ resolve }) => resolve(typeof newToken === 'string' ? newToken : newToken.access_token));
        _refreshQueue = [];
        original.headers['Authorization'] = `Bearer ${typeof newToken === 'string' ? newToken : newToken.access_token}`;
        return apiClient(original);
      } catch (refreshErr) {
        _refreshQueue.forEach(({ reject }) => reject(refreshErr));
        _refreshQueue = [];
        const { default: useAuthStore } = await import('../stores/auth.store');
        useAuthStore.getState().logout();
        return Promise.reject(refreshErr);
      } finally {
        _isRefreshing = false;
      }
    }

    const message =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      'Unknown error';

    const normalized = new Error(message);
    normalized.status = error?.response?.status;
    normalized.data = error?.response?.data;
    return Promise.reject(normalized);
  }
);

export const authApi = {
  register: (data) => apiClient.post('/api/auth/register', data),
  login: (data) => apiClient.post('/api/auth/login', data),
  refresh: (data) => apiClient.post('/api/auth/refresh', data),
  me: () => apiClient.get('/api/auth/me'),
};

export const healthApi = {
  check: () => apiClient.get('/api/health'),
  dbCheck: () => apiClient.get('/api/health/db'),
  full: () => apiClient.get('/api/health/full'),
};

export const agentsApi = {
  list: (params) => apiClient.get('/api/agents', { params }),
  get: (id) => apiClient.get(`/api/agents/${id}`),
  create: (data) => apiClient.post('/api/agents', data),
  update: (id, data) => apiClient.patch(`/api/agents/${id}`, data),
  delete: (id) => apiClient.delete(`/api/agents/${id}`),
  start: (id) => apiClient.post(`/api/agents/${id}/start`),
  stop: (id) => apiClient.post(`/api/agents/${id}/stop`),
  pause: (id) => apiClient.post(`/api/agents/${id}/pause`),
  emergencyStop: () => apiClient.post('/api/agents/emergency-stop'),
};

export const tradesApi = {
  list: (params) => apiClient.get('/api/trades', { params }),
  get: (id) => apiClient.get(`/api/trades/${id}`),
  getByAgent: (agentId, params) => apiClient.get(`/api/agents/${agentId}/trades`, { params }),
  export: (agentId = null) => {
    const params = agentId ? `?agent_id=${agentId}` : '';
    const token = localStorage.getItem('auth_access_token');
    return fetch(`${API_BASE_URL}/api/trades/export${params}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }).then((r) => r.blob()).then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'labourious_trades.csv';
      a.click();
      URL.revokeObjectURL(url);
    });
  },
};

export const performanceApi = {
  summary: () => apiClient.get('/api/performance/summary'),
  byAgent: (agentId, params) => apiClient.get(`/api/agents/${agentId}/performance`, { params }),
  portfolio: (params) => apiClient.get('/api/performance/portfolio', { params }),
};

export const dashboardApi = {
  summary: () => apiClient.get('/api/dashboard/summary'),
  performance: () => apiClient.get('/api/dashboard/performance'),
  equityCurve: (days = 30) => apiClient.get('/api/dashboard/equity-curve', { params: { days } }),
  allocation: () => apiClient.get('/api/dashboard/allocation'),
  risk: () => apiClient.get('/api/dashboard/risk'),
};

export const vaultApi = {
  listKeys: () => apiClient.get('/api/vault/keys'),
  setKey: (data) => apiClient.post('/api/vault/set', data),
  deleteKey: (key) => apiClient.delete(`/api/vault/keys/${key}`),
  testConnection: (exchange) => apiClient.post(`/api/vault/test/${exchange}`),
};

export const analyticsApi = {
  portfolio: () => apiClient.get('/api/analytics/portfolio'),
  equityCurve: (days = 30, agentId = null) => {
    const params = new URLSearchParams({ days });
    if (agentId != null) params.append('agent_id', agentId);
    return apiClient.get(`/api/analytics/equity-curve?${params}`);
  },
  leaderboard: (sortBy = 'return') =>
    apiClient.get(`/api/analytics/leaderboard?sort_by=${sortBy}`),
  correlation: () => apiClient.get('/api/analytics/correlation'),
  attribution: (dateStr = null) => {
    const url = dateStr
      ? `/api/analytics/attribution?date=${dateStr}`
      : '/api/analytics/attribution';
    return apiClient.get(url);
  },
};

export const backtestApi = {
  run: (payload) => apiClient.post('/api/backtest/run', payload),
  poll: (runId) => apiClient.get(`/api/backtest/${runId}`),
  history: (agentId = null) => {
    const url = agentId != null
      ? `/api/backtest/history?agent_id=${agentId}`
      : '/api/backtest/history';
    return apiClient.get(url);
  },
};

export const llmApi = {
  getConfig: () => apiClient.get('/api/llm/config'),
  patchConfig: (data) => apiClient.patch('/api/llm/config', data),
  test: () => apiClient.post('/api/llm/test'),
  saveKey: (keyName, value) => apiClient.post('/api/llm/key', { key_name: keyName, value }),
  getCost: (provider, model, checkFrequency) =>
    apiClient.get(`/api/llm/cost`, { params: { provider, model, check_frequency: checkFrequency } }),
};

export const notificationsApi = {
  getPreferences: () => apiClient.get('/api/notifications/preferences'),
  updatePreferences: (data) => apiClient.patch('/api/notifications/preferences', data),
  sendTest: () => apiClient.post('/api/notifications/test'),
};

export const brokersApi = {
  list: () => apiClient.get('/api/brokers'),
  available: () => apiClient.get('/api/brokers/available'),
  connect: (data) => apiClient.post('/api/brokers/connect', data),
  test: (name) => apiClient.get(`/api/brokers/${name}/test`),
};

export const roomLayoutsApi = {
  get: (roomKey) => apiClient.get(`/api/room-layouts/${roomKey}`),
  save: (roomKey, mapData) => apiClient.put(`/api/room-layouts/${roomKey}`, { map_json: mapData }),
  reset: (roomKey) => apiClient.delete(`/api/room-layouts/${roomKey}`),
};

export const agentAppearanceApi = {
  get: (agentId) => apiClient.get(`/api/agents/${agentId}/appearance`),
  save: (agentId, appearance) => apiClient.put(`/api/agents/${agentId}/appearance`, { appearance }),
  getUserAvatar: () => apiClient.get('/api/user/avatar-appearance'),
  saveUserAvatar: (appearance) => apiClient.put('/api/user/avatar-appearance', { appearance }),
};

export const settingsApi = {
  get: () => apiClient.get('/api/settings'),
  patchAllocation: (data) => apiClient.post('/api/settings/allocation', data),
  changePassword: (data) => apiClient.post('/api/settings/vault-password', data),
};

export default apiClient;
