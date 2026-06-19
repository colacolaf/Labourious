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
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
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

export const healthApi = {
  check: () => apiClient.get('/api/health'),
  dbCheck: () => apiClient.get('/api/health/db'),
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
};

export const tradesApi = {
  list: (params) => apiClient.get('/api/trades', { params }),
  get: (id) => apiClient.get(`/api/trades/${id}`),
  getByAgent: (agentId, params) => apiClient.get(`/api/agents/${agentId}/trades`, { params }),
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

export default apiClient;
