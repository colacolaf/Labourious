// Minimal self-check for TradingAgent's non-Phaser-rendering logic: the confidence tint
// thresholds (ported from AgentInspector.jsx's confColor) and the paused/trade/processing
// branches. Uses a hand-rolled fake Phaser scene so this stays free of Phaser's jsdom import
// issues (same reasoning as lib/__tests__/map-loader.test.js).
import { TradingAgent } from '../TradingAgent';

function makeFakeScene() {
  const sprite = {
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
    add: { sprite: jest.fn(() => sprite) },
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
