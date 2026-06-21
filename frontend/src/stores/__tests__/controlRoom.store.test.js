import { renderHook, act } from '@testing-library/react';
import useControlRoomStore from '../controlRoom.store';
import { brokersApi, llmApi, agentsApi, settingsApi } from '../../utils/api-client';

jest.mock('../../utils/api-client', () => ({
  brokersApi: {
    list: jest.fn(),
    available: jest.fn(),
    connect: jest.fn(),
    test: jest.fn(),
  },
  llmApi: {
    getConfig: jest.fn(),
    patchConfig: jest.fn(),
    test: jest.fn(),
  },
  agentsApi: {
    list: jest.fn(),
    start: jest.fn(),
    stop: jest.fn(),
    pause: jest.fn(),
  },
  settingsApi: {
    get: jest.fn(),
    patchAllocation: jest.fn(),
    changePassword: jest.fn(),
  },
}));

beforeEach(() => {
  jest.clearAllMocks();
  // reset store between tests
  useControlRoomStore.setState({
    brokers: [], availableBrokers: [], llmConfig: null,
    agents: [], settings: null, loading: false, error: null, saving: false,
  });
});

test('fetchBrokers sets brokers and availableBrokers', async () => {
  brokersApi.list.mockResolvedValue([{ broker_name: 'alpaca', is_active: true }]);
  brokersApi.available.mockResolvedValue({ brokers: ['alpaca', 'binance'] });

  const { result } = renderHook(() => useControlRoomStore());
  await act(async () => { await result.current.fetchBrokers(); });

  expect(result.current.brokers).toEqual([{ broker_name: 'alpaca', is_active: true }]);
  expect(result.current.availableBrokers).toEqual(['alpaca', 'binance']);
  expect(result.current.loading).toBe(false);
  expect(result.current.error).toBeNull();
});

test('fetchBrokers sets error on failure', async () => {
  brokersApi.list.mockRejectedValue(new Error('network error'));
  brokersApi.available.mockResolvedValue({ brokers: [] });

  const { result } = renderHook(() => useControlRoomStore());
  await act(async () => { await result.current.fetchBrokers(); });

  expect(result.current.error).toBe('network error');
  expect(result.current.loading).toBe(false);
});

test('startAgent updates agent status in state', async () => {
  agentsApi.start.mockResolvedValue({ id: '1', status: 'running' });
  useControlRoomStore.setState({ agents: [{ id: '1', status: 'stopped', name: 'A' }] });

  const { result } = renderHook(() => useControlRoomStore());
  await act(async () => { await result.current.startAgent('1'); });

  expect(result.current.agents[0].status).toBe('running');
});

test('saveAllocation calls settingsApi.patchAllocation and sets saving false', async () => {
  settingsApi.patchAllocation.mockResolvedValue({ status: 'updated' });

  const { result } = renderHook(() => useControlRoomStore());
  await act(async () => {
    await result.current.saveAllocation({ max_portfolio_drawdown: 0.2, default_position_size: 0.05, max_agents: 20 });
  });

  expect(settingsApi.patchAllocation).toHaveBeenCalledWith({ max_portfolio_drawdown: 0.2, default_position_size: 0.05, max_agents: 20 });
  expect(result.current.saving).toBe(false);
});

test('testLLM returns result from llmApi.test', async () => {
  llmApi.test.mockResolvedValue({ ok: true, latency_ms: 120 });

  const { result } = renderHook(() => useControlRoomStore());
  let res;
  await act(async () => { res = await result.current.testLLM(); });

  expect(res).toEqual({ ok: true, latency_ms: 120 });
});
