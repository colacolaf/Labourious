// Floating notification bubble above a TradingAgent's sprite head. Modern flat style per the
// frozen design spec (docs/superpowers/specs/2026-07-04-deskrpg-redesign-design.md, "Head
// Bubble Events" — rgba(15,23,42,0.92) rounded rect, 1px border, 11px mono). Deliberately NOT
// the CRT/scanline/Press Start 2P look used by this repo's deprecated Pixi warroom — that's a
// hard anti-goal for the whole Phase 11 redesign.
//
// One HeadBubble per TradingAgent, holding up to 2 stacked slots (per spec: "queue support
// (max 2 stacked bubbles)"). A 3rd+ concurrent bubble waits in a small FIFO queue until a slot
// frees up rather than instantly replacing what's showing.

const BG_COLOR = 0x0f172a; // rgba(15,23,42,...)
const BG_ALPHA = 0.92;
const OFFSET_Y = -52; // relative to sprite y, per spec
const SLOT_HEIGHT = 20; // vertical spacing between stacked slots
const PAD_X = 6;
const BOX_H = 16;
const FADE_MS = 500;
const FLOAT_PX = 12;

// JetBrains Mono isn't loaded as a web font anywhere in this app (no @font-face / <link> in
// index.html or styles/index.css) — this silently renders as the 'monospace' fallback until a
// real font is wired up. Noting as a minor gap rather than a blocker for this task.
const FONT_FAMILY = "'JetBrains Mono', monospace";

const TYPE_STYLE = {
  trade_win: { color: 0x22c55e, durationMs: 3000 },
  trade_loss: { color: 0xef4444, durationMs: 3000 },
  approval: { color: 0xf59e0b, persistent: true },
  paused: { color: 0xfb923c, persistent: true },
  processing: { color: 0xffffff, durationMs: 1500, spinner: true },
  confidence: { color: 0xffffff, durationMs: 1500 },
};

export class HeadBubble {
  constructor(scene, sprite) {
    this.scene = scene;
    this.sprite = sprite;
    this.container = scene.add.container(sprite.x, sprite.y + OFFSET_Y);
    this.container.setDepth(1000); // above tiles/decor/other sprites, which top out around depth ~30
    this.slots = [this._makeSlot(), this._makeSlot()];
    this.active = []; // entries currently occupying a slot; index 0 = closest to the head
    this.queue = []; // FIFO overflow beyond the 2 slots
  }

  _makeSlot() {
    const bg = this.scene.add.graphics().setVisible(false);
    const icon = this.scene.add.graphics().setVisible(false); // spinner arc for 'processing' only
    const text = this.scene.add.text(0, 0, '', {
      fontFamily: FONT_FAMILY,
      fontSize: '11px',
      color: '#e2e8f0',
    }).setOrigin(0.5).setVisible(false);
    this.container.add([bg, icon, text]);
    return { bg, icon, text };
  }

  show(type, text, opts = {}) {
    const style = TYPE_STYLE[type] || {};
    const entry = {
      type,
      label: text,
      color: opts.color ?? style.color ?? 0xffffff,
      durationMs: opts.durationMs ?? style.durationMs ?? 2000,
      persistent: opts.persistent ?? style.persistent ?? false,
      spinner: !!style.spinner,
      countdownSeconds: opts.countdownSeconds ?? null,
      lastRemaining: null, // throttles countdown redraws in tick() to once per displayed second
      elapsed: 0,
      spinRot: 0,
    };

    const activeIdx = this.active.findIndex((e) => e.type === type);
    if (activeIdx !== -1) {
      this.active[activeIdx] = entry;
      this._render(activeIdx);
      return;
    }
    const queueIdx = this.queue.findIndex((e) => e.type === type);
    if (queueIdx !== -1) {
      this.queue[queueIdx] = entry; // still waiting — nothing visible to update yet
      return;
    }

    // Anything already queued gets first claim on a free slot — a brand-new type must not cut
    // in line ahead of what's been waiting longer.
    this._promote();
    if (this.active.length < this.slots.length) {
      this.active.push(entry);
    } else {
      this.queue.push(entry);
    }
    this._renderAll();
  }

  clear(type) {
    const idx = this.active.findIndex((e) => e.type === type);
    if (idx === -1) {
      this.queue = this.queue.filter((e) => e.type !== type);
      return;
    }
    this.active.splice(idx, 1);
    this._promote();
    this._renderAll();
  }

  // Drains as many queued entries as fit into free slots — not just one — so multiple
  // simultaneous expirations (or a clear()) don't starve the queue down one slot at a time.
  _promote() {
    while (this.queue.length > 0 && this.active.length < this.slots.length) {
      this.active.push(this.queue.shift());
    }
  }

  tick(delta) {
    this.container.setPosition(this.sprite.x, this.sprite.y + OFFSET_Y);
    if (this.active.length === 0) return;

    let anyExpired = false;
    this.active.forEach((entry, i) => {
      entry.elapsed += delta;
      const slot = this.slots[i];
      const baseY = -i * SLOT_HEIGHT;

      if (entry.spinner) {
        entry.spinRot += delta * 0.008;
        this._drawSpinner(slot.icon, entry.color, entry.spinRot);
      }

      if (entry.countdownSeconds != null) {
        const remaining = Math.max(0, Math.ceil(entry.countdownSeconds - entry.elapsed / 1000));
        if (remaining !== entry.lastRemaining) {
          entry.lastRemaining = remaining;
          slot.text.setText(`${entry.label} ${remaining}s`);
          this._resize(slot, entry, baseY);
        }
        if (remaining <= 0) { entry.expired = true; anyExpired = true; }
      } else if (!entry.persistent) {
        const floatT = Math.min(1, entry.elapsed / entry.durationMs);
        const y = baseY - floatT * FLOAT_PX;
        slot.bg.setY(y);
        slot.icon.setY(y);
        slot.text.setY(y);

        const fadeStart = entry.durationMs - FADE_MS;
        if (entry.elapsed >= fadeStart) {
          const alpha = Math.max(0, 1 - (entry.elapsed - fadeStart) / FADE_MS);
          slot.bg.setAlpha(alpha * BG_ALPHA);
          slot.icon.setAlpha(alpha);
          slot.text.setAlpha(alpha);
        }
        if (entry.elapsed >= entry.durationMs) { entry.expired = true; anyExpired = true; }
      }
    });

    if (anyExpired) {
      this.active = this.active.filter((e) => !e.expired);
      this._promote();
      this._renderAll();
    }
  }

  _renderAll() {
    this.slots.forEach((slot) => {
      slot.bg.setVisible(false);
      slot.icon.setVisible(false);
      slot.text.setVisible(false);
    });
    this.active.forEach((_, i) => this._render(i));
  }

  _render(i) {
    const entry = this.active[i];
    const slot = this.slots[i];
    const baseY = -i * SLOT_HEIGHT;

    slot.text.setColor(`#${entry.color.toString(16).padStart(6, '0')}`);
    slot.text.setText(entry.spinner ? '' : entry.label);
    slot.text.setAlpha(1);
    slot.text.setVisible(!entry.spinner);

    slot.icon.setAlpha(1);
    slot.icon.setVisible(entry.spinner);
    if (entry.spinner) this._drawSpinner(slot.icon, entry.color, entry.spinRot);

    this._resize(slot, entry, baseY);
  }

  // Recomputes the rounded-rect bg size from current text width and repositions bg/icon/text
  // at `baseY` (the stack slot's resting position, before any float/fade offset).
  _resize(slot, entry, baseY) {
    slot.text.setPosition(0, baseY);
    slot.icon.setPosition(0, baseY);

    if (entry.spinner) {
      slot.bg.setVisible(false);
      return;
    }
    const w = Math.max(24, slot.text.width + PAD_X * 2);
    slot.bg.clear();
    slot.bg.setPosition(0, baseY);
    slot.bg.setAlpha(BG_ALPHA);
    slot.bg.fillStyle(BG_COLOR, 1);
    slot.bg.fillRoundedRect(-w / 2, -BOX_H / 2, w, BOX_H, 4);
    slot.bg.lineStyle(1, entry.color, 1);
    slot.bg.strokeRoundedRect(-w / 2, -BOX_H / 2, w, BOX_H, 4);
    slot.bg.setVisible(true);
  }

  _drawSpinner(gfx, color, rotation) {
    gfx.clear();
    gfx.lineStyle(2, color, 1);
    gfx.beginPath();
    gfx.arc(0, 0, 6, rotation, rotation + Math.PI * 1.4);
    gfx.strokePath();
    gfx.setVisible(true);
  }

  destroy() {
    this.container.destroy();
  }
}
