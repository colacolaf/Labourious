// Self-check for HeadBubble's stacking/queueing/expiry logic (the actual branching logic Task 8
// adds) — not a full Phaser render test, just enough of a fake scene to drive show/tick/clear.
import { HeadBubble } from '../HeadBubble';

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
  return {
    add: {
      container: jest.fn(() => ({
        setDepth: jest.fn().mockReturnThis(),
        setPosition: jest.fn(),
        add: jest.fn(),
        destroy: jest.fn(),
      })),
      graphics: jest.fn(() => makeFakeGraphics()),
      text: jest.fn(() => makeFakeText()),
    },
  };
}

test('stacks up to 2 bubbles, queues the 3rd, and promotes it once a slot frees', () => {
  const bubble = new HeadBubble(makeFakeScene(), { x: 0, y: 0 });

  bubble.show('trade_win', '✅ +$100');
  bubble.show('processing', '');
  bubble.show('confidence', '80%'); // 3rd concurrent type — should queue, not replace

  expect(bubble.active.map((e) => e.type)).toEqual(['trade_win', 'processing']);
  expect(bubble.queue.map((e) => e.type)).toEqual(['confidence']);

  bubble.clear('trade_win');
  expect(bubble.active.map((e) => e.type)).toEqual(['processing', 'confidence']);
  expect(bubble.queue).toHaveLength(0);
});

test('re-showing an already-active type updates in place instead of stacking a duplicate', () => {
  const bubble = new HeadBubble(makeFakeScene(), { x: 0, y: 0 });
  bubble.show('confidence', '50%');
  bubble.show('confidence', '90%');
  expect(bubble.active).toHaveLength(1);
  expect(bubble.active[0].label).toBe('90%');
});

test('finite-duration bubbles expire after their durationMs and are removed on tick', () => {
  const bubble = new HeadBubble(makeFakeScene(), { x: 0, y: 0 });
  bubble.show('trade_win', '✅ +$100', { durationMs: 1000 });
  bubble.tick(500);
  expect(bubble.active).toHaveLength(1);
  bubble.tick(600); // elapsed now 1100 > 1000
  expect(bubble.active).toHaveLength(0);
});

test('approval countdown self-clears at 0 with no external resolution event', () => {
  const bubble = new HeadBubble(makeFakeScene(), { x: 0, y: 0 });
  bubble.show('approval', '⚠️ Approve?', { persistent: true, countdownSeconds: 5 });
  bubble.tick(4000);
  expect(bubble.active).toHaveLength(1);
  bubble.tick(1001); // elapsed 5001ms > 5s countdown
  expect(bubble.active).toHaveLength(0);
});

test('persistent non-countdown bubbles (paused) never auto-expire', () => {
  const bubble = new HeadBubble(makeFakeScene(), { x: 0, y: 0 });
  bubble.show('paused', '🔒 Losing streak');
  bubble.tick(60000);
  expect(bubble.active).toHaveLength(1);
  bubble.clear('paused');
  expect(bubble.active).toHaveLength(0);
});
