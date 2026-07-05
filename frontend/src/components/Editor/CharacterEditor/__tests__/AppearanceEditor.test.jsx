// Basic render smoke test. Mocks the registry/api/compositor modules so this doesn't depend
// on a real fetch, backend, or jsdom's unimplemented canvas 2d context (same reasoning as
// TradingAgent.test.js mocking sprite-compositor).
//
// ponytail: react-scripts' jest preset sets `resetMocks: true`, which wipes any
// mockImplementation set inside a jest.mock(path, factory) before every test — so
// implementations must be re-applied in beforeEach rather than baked into the factory.
import { render, screen } from '@testing-library/react';

jest.mock('../../../../lib/lpc-registry');
jest.mock('../../../../lib/sprite-compositor');
jest.mock('../../../../utils/api-client');

import { loadRegistry, getItemVariants } from '../../../../lib/lpc-registry';
import { compositeCharacter } from '../../../../lib/sprite-compositor';
import { agentAppearanceApi } from '../../../../utils/api-client';
import AppearanceEditor from '../AppearanceEditor';

const REGISTRY = {
  bodyTypes: ['male', 'female'],
  categories: [
    { id: 'hair', label: 'Hair', items: [{ key: 'hair_parted', name: 'Parted', variants: ['black', 'blonde'] }] },
  ],
};

beforeEach(() => {
  loadRegistry.mockResolvedValue(REGISTRY);
  getItemVariants.mockImplementation((item) => item?.variants || []);
  compositeCharacter.mockResolvedValue();
  agentAppearanceApi.get.mockResolvedValue({ appearance: null });
  agentAppearanceApi.save.mockResolvedValue({ appearance: {} });
  agentAppearanceApi.getUserAvatar.mockResolvedValue({ appearance: null });
  agentAppearanceApi.saveUserAvatar.mockResolvedValue({ appearance: {} });
});

test('renders category pickers and body type toggle after registry loads', async () => {
  render(<AppearanceEditor agentId={5} />);

  await screen.findByText('Hair');
  // ponytail: no @testing-library/jest-dom setup in this project (no setupTests.js) —
  // getByText already throws if not found, so a truthy check is enough, no toBeInTheDocument.
  expect(screen.getByText('male')).toBeTruthy();
  expect(screen.getByText('female')).toBeTruthy();
  expect(agentAppearanceApi.get).toHaveBeenCalledWith(5);
});

test('editing the user avatar (no agentId) fetches the user avatar endpoint', async () => {
  render(<AppearanceEditor />);
  await screen.findByText('Hair');
  expect(agentAppearanceApi.getUserAvatar).toHaveBeenCalled();
});
