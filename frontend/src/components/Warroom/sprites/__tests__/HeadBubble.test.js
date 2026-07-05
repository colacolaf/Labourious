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

test('show() called twice for a type already sitting in queue updates it in place, no duplicate', () => {
  const bubble = new HeadBubble(makeFakeScene(), { x: 0, y: 0 });
  bubble.show('trade_win', 'A'); // fills slot 0
  bubble.show('processing', ''); // fills slot 1
  bubble.show('confidence', '50%'); // slots full -> queued
  bubble.show('confidence', '90%'); // same type, still queued -> must update, not push a 2nd copy

  expect(bubble.queue).toHaveLength(1);
  expect(bubble.queue[0].label).toBe('90%');

  bubble.clear('trade_win'); // frees a slot -> promotes the (single, updated) queued entry
  expect(bubble.active.filter((e) => e.type === 'confidence')).toHaveLength(1);
  expect(bubble.queue).toHaveLength(0);
});

test('multiple active entries expiring on the same tick() promote all waiting queue entries, not just one', () => {
  const bubble = new HeadBubble(makeFakeScene(), { x: 0, y: 0 });
  bubble.show('trade_win', 'A', { durationMs: 1000 });
  bubble.show('trade_loss', 'B', { durationMs: 1000 }); // both slots full, both expire together
  bubble.show('confidence', 'C'); // queued
  bubble.show('paused', 'D'); // also queued

  expect(bubble.queue).toHaveLength(2);

  bubble.tick(1100); // both active entries cross their 1000ms durationMs in the same tick

  expect(bubble.active.map((e) => e.type)).toEqual(['confidence', 'paused']);
  expect(bubble.queue).toHaveLength(0);
});
