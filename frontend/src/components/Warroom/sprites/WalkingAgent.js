import { Agent } from './Agent';

function rectHit(px, py, r, rx, ry, rw, rh) {
  return px + r > rx && px - r < rx + rw && py + r > ry && py - r < ry + rh;
}

export class WalkingAgent extends Agent {
  constructor(app, x, y, bodyColor, headColor, borderColor, vestColor, bounds, blockedRects) {
    super(app, x, y, bodyColor, headColor, borderColor, vestColor);
    this.bounds = bounds;
    this.blocked = blockedRects;
    this.retarget();
  }

  retarget() {
    for (let t = 0; t < 12; t++) {
      const tx = this.bounds.x0 + Math.random() * (this.bounds.x1 - this.bounds.x0);
      const ty = this.bounds.y0 + Math.random() * (this.bounds.y1 - this.bounds.y0);
      if (!this.blocked.some(b => rectHit(tx, ty, 6, b.x, b.y, b.w, b.h))) {
        this.tx = tx;
        this.ty = ty;
        return;
      }
    }
    this.tx = (this.bounds.x0 + this.bounds.x1) / 2;
    this.ty = (this.bounds.y0 + this.bounds.y1) / 2;
  }

  tick(tradeTexts, _wanderRadius, spinSpeed) {
    for (const b of this.blocked) {
      if (rectHit(this.x, this.y, 5, b.x, b.y, b.w, b.h)) {
        const cx = b.x + b.w / 2;
        const cy = b.y + b.h / 2;
        const dx = this.x - cx;
        const dy = this.y - cy;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        this.x += (dx / d) * 3;
        this.y += (dy / d) * 3;
      }
    }
    super.tick(tradeTexts, 0, spinSpeed || 0.08);
  }
}
