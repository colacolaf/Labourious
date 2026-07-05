// Minimal self-check for TradingAgent's non-Phaser-rendering logic: the confidence tint
// thresholds (ported from AgentInspector.jsx's confColor) and the paused/trade/processing
// branches. Uses a hand-rolled fake Phaser scene so this stays free of Phaser's jsdom import
// issues (same reasoning as lib/__tests__/map-loader.test.js).
jest.mock('../../../../lib/sprite-compositor', () => ({
  compositeCharacter: jest.fn(() => Promise.resolve()),
}));

import { TradingAgent } from '../TradingAgent';

// Chainable fake for Phaser Graphics/Text/Container — just enough surface for HeadBubble (see
// ../HeadBubble.js) to construct and run its show/tick/clear logic without throwing.
function makeFakeGraphics() {
  const gfx = {};
  ['clear', 'setPosition', 'setAlpha', 'setVisible', 'fillStyle', 'fillRoundedRect',
    'lineStyle', 'strokeRoundedRect', 'setY', 'beginPath', 'strokePath', 'arc']
    .forEach((m) => { gfx[m] = jest.fn().mockReturnValue(gfx); });
  return gfx;
}

function makeFakeText() {
  const text = { width: 40 };
  ['setOrigin', 'setVisible', 'setPosition', 'setAlpha', 'setColor', 'setText', 'setY']
    .forEach((m) => { text[m] = jest.fn().mockReturnValue(text); });
  return text;
}

function makeFakeScene() {
  const sprite = {
    x: 0,
    y: 0,
    setOrigin: jest.fn().mockReturnThis(),
    setDisplaySize: jest.fn().mockReturnThis(),
    setInteractive: jest.fn().mockReturnThis(),
    setTint: jest.fn(),
    setAlpha: jest.fn(),
    setTexture: jest.fn(),
    on: jest.fn(),
    destroy: jest.fn(),
    scene: {},
  };
  const scene = {
    add: {
      sprite: jest.fn(() => sprite),
      container: jest.fn(() => ({
        setDepth: jest.fn().mockReturnThis(),
        setPosition: jest.fn(),
        add: jest.fn(),
        destroy: jest.fn(),
      })),
      graphics: jest.fn(() => makeFakeGraphics()),
      text: jest.fn(() => makeFakeText()),
    },
    time: { delayedCall: jest.fn() },
    textures: { addCanvas: jest.fn(() => ({ add: jest.fn() })) },
  };
  return scene;
}

test('setConfidence tints by threshold', () => {
  const agent = new TradingAgent(makeFakeScene(), 0, 0, 'fallback-char');

  agent.setConfidence(80);
  expect(agent.sprite.setTint).toHaveBeenLastCalledWith(0x00ff88);

  agent.setConfidence(50);
  expect(agent.sprite.setTint).toHaveBeenLastCalledWith(0xff8c00);

  agent.setConfidence(10);
  expect(agent.sprite.setTint).toHaveBeenLastCalledWith(0xff4444);
});

test('setPaused toggles alpha; onTrade/onProcessing/destroy do not throw', () => {
  const agent = new TradingAgent(makeFakeScene(), 0, 0, 'fallback-char');

  agent.setPaused(true);
  expect(agent.sprite.setAlpha).toHaveBeenLastCalledWith(0.45);
  agent.setPaused(false);
  expect(agent.sprite.setAlpha).toHaveBeenLastCalledWith(1);

  expect(() => agent.onTrade('AAPL', 'BUY', 100)).not.toThrow();
  expect(() => agent.onProcessing()).not.toThrow();

  agent.destroy();
  expect(agent.sprite.destroy).toHaveBeenCalled();
});

test('applyAppearance re-applies displaySize after the real texture swap (regression: 1x1 fallback-char bakes a 48x scale)', async () => {
  const agent = new TradingAgent(makeFakeScene(), 0, 0, 'fallback-char');
  agent.sprite.setDisplaySize.mockClear();

  await agent.applyAppearance({ bodyType: 'male', layers: {} });

  expect(agent.sprite.setTexture).toHaveBeenCalledWith(expect.stringContaining('agent-appearance-'), 0);
  // setTexture swaps in the real 64x64 composited frame, which recomputes scale against the
  // stale 48/1 factor unless setDisplaySize is called again — assert it is.
  expect(agent.sprite.setDisplaySize).toHaveBeenLastCalledWith(48, 48);
});
