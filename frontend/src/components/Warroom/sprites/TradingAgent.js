// One agent sprite in a Phaser warroom scene. Wraps a Phaser.Sprite positioned at an
// agentSlot's pixel coords; WarroomScene owns spawning/matching, this class owns the visual.
//
// Trade/processing/paused/confidence feedback keeps the tint-flash as a secondary cue (per the
// design spec's own example: flash body color alongside the bubble) and adds a floating
// HeadBubble above the sprite's head for the real notification content — see HeadBubble.js and
// the frozen design spec's "Head Bubble Events" table.
import { compositeCharacter } from '../../../lib/sprite-compositor';
import { HeadBubble } from './HeadBubble';

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
    this.headBubble = new HeadBubble(scene, this.sprite);
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
    // setTexture swaps in the real 64x64 LPC frame but doesn't recompute scale — the initial
    // setDisplaySize(48,48) baked scale against the 1x1 fallback-char placeholder, so it must
    // be re-applied here or the sprite renders 64x too large.
    this.sprite.setDisplaySize(48, 48);
  }

  // Tint-flash (secondary cue) + floating win/loss HeadBubble (primary — spec's content column).
  onTrade(symbol, action, pnl) {
    const win = pnl >= 0;
    const flashColor = win ? 0x22c55e : 0xef4444;
    this.sprite.setTint(flashColor);
    this.scene.time.delayedCall(400, () => this.sprite.setTint(this._confidenceTint));
    const amount = Math.abs(pnl).toFixed(0);
    this.headBubble.show(win ? 'trade_win' : 'trade_loss', `${win ? '✅ +' : '❌ -'}$${amount}`);
    // Trade executing/resolving always clears any pending-approval bubble for this agent —
    // it's the only reliable "resolved" signal we get back over WS (see showApproval below).
    this.headBubble.clear('approval');
  }

  // Tint-flash + spinning-arc HeadBubble (no text, per spec).
  onProcessing() {
    this.sprite.setTint(0xffffff);
    this.scene.time.delayedCall(300, () => this.sprite.setTint(this._confidenceTint));
    this.headBubble.show('processing', '');
  }

  setPaused(paused, reason) {
    this.sprite.setAlpha(paused ? 0.45 : 1);
    if (paused) {
      this.headBubble.show('paused', `🔒 ${reason || 'Losing streak'}`);
    } else {
      this.headBubble.clear('paused');
    }
  }

  // `showBubble`: opt-in so routine poll/store-sync calls (which fire on every render) don't
  // spam a bubble — only pass true from an actual live WS event (see useWarroomAgents.js).
  setConfidence(score, { showBubble = false } = {}) {
    this._confidenceTint = score >= 70 ? CONFIDENCE_HIGH : score >= 35 ? CONFIDENCE_MID : CONFIDENCE_LOW;
    this.sprite.setTint(this._confidenceTint);
    if (showBubble) {
      this.headBubble.show('confidence', `${Math.round(score)}%`, { color: this._confidenceTint });
    }
  }

  // Backend's real event is `trade_approval_required` (backend/trading/trade_executor.py) with
  // a 30s server-side timeout. There's no WS event on manual approve/reject — approve resolves
  // via a later `trade_executed` broadcast (cleared in onTrade above) and manual reject sends
  // nothing back at all — so the bubble runs its own countdown and self-clears at 0 as the safe
  // default, independent of any WS follow-up.
  showApproval(timeoutSeconds = 30) {
    this.headBubble.show('approval', '⚠️ Approve?', { persistent: true, countdownSeconds: timeoutSeconds });
  }

  clearApproval() {
    this.headBubble.clear('approval');
  }

  // Forwarded from WarroomScene.update() so the bubble can float/fade/spin per-frame.
  tick(delta) {
    this.headBubble.tick(delta);
  }

  destroy() {
    this.headBubble.destroy();
    this.sprite.destroy();
  }
}
