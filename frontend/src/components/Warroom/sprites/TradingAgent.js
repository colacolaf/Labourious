// One agent sprite in a Phaser warroom scene. Wraps a Phaser.Sprite positioned at an
// agentSlot's pixel coords; WarroomScene owns spawning/matching, this class owns the visual.
//
// Trade/processing/paused/confidence feedback here is deliberately minimal (tint flashes) —
// Task 8 replaces/extends it with the floating HeadBubble system from the frozen design spec
// (docs/superpowers/specs/2026-07-04-deskrpg-redesign-design.md, "Head Bubble Events" table).
import { compositeCharacter } from '../../../lib/sprite-compositor';

const FRAME_SIZE = 64;
// LPC universal sheet row order: 0=up, 1=left, 2=down, 3=right. We only need a single static
// "down" pose for now — full 9-col walk-cycle animation is out of scope for this task.
const DOWN_ROW = 2;

// Tint thresholds ported from AgentInspector.jsx's OverviewTab confColor logic, so the sprite's
// body tint always agrees with the inspector panel's confidence color.
const CONFIDENCE_HIGH = 0x00ff88;
const CONFIDENCE_MID = 0xff8c00;
const CONFIDENCE_LOW = 0xff4444;

let textureSeq = 0; // ponytail: monotonic id keeps each composited canvas texture's key unique; no cleanup of old textures yet, add when agent count/churn makes it matter

export class TradingAgent {
  constructor(scene, x, y, textureKey = 'fallback-char') {
    this.scene = scene;
    this.id = null;
    this._confidenceTint = 0xffffff;
    this.sprite = scene.add.sprite(x, y, textureKey);
    this.sprite.setOrigin(0.5, 0.85);
    this.sprite.setDisplaySize(48, 48);
    this.sprite.setInteractive({ useHandCursor: true });
  }

  // Composites `appearance` onto an offscreen canvas, registers it as a new Phaser canvas
  // texture, and points the sprite at its "down" idle frame.
  async applyAppearance(appearance) {
    const canvas = document.createElement('canvas');
    await compositeCharacter(canvas, appearance);
    if (!this.sprite || !this.sprite.scene) return; // ponytail: sprite destroyed while compositing — drop the result rather than crash
    const key = `agent-appearance-${textureSeq++}`;
    const texture = this.scene.textures.addCanvas(key, canvas);
    texture.add(0, 0, 0, DOWN_ROW * FRAME_SIZE, FRAME_SIZE, FRAME_SIZE);
    this.sprite.setTexture(key, 0);
  }

  // Minimal trade feedback for now — Task 8 adds the real floating trade-result bubble.
  onTrade(symbol, action, pnl) {
    const flashColor = pnl >= 0 ? 0x22c55e : 0xef4444;
    this.sprite.setTint(flashColor);
    this.scene.time.delayedCall(400, () => this.sprite.setTint(this._confidenceTint));
  }

  // Minimal processing feedback for now — Task 8 adds the real spinning-arc bubble.
  onProcessing() {
    this.sprite.setTint(0xffffff);
    this.scene.time.delayedCall(300, () => this.sprite.setTint(this._confidenceTint));
  }

  setPaused(paused) {
    this.sprite.setAlpha(paused ? 0.45 : 1);
  }

  setConfidence(score) {
    this._confidenceTint = score >= 70 ? CONFIDENCE_HIGH : score >= 35 ? CONFIDENCE_MID : CONFIDENCE_LOW;
    this.sprite.setTint(this._confidenceTint);
  }

  destroy() {
    this.sprite.destroy();
  }
}
