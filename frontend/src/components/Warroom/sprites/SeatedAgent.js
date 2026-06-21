import { Agent } from './Agent';

export class SeatedAgent extends Agent {
  constructor(app, x, y, bodyColor, headColor, borderColor, vestColor, wanderRadius = 6) {
    super(app, x, y, bodyColor, headColor, borderColor, vestColor);
    this.bx = x;
    this.by = y;
    this.wanderRadius = wanderRadius;
    this.spd = 0.25;
    this.retarget();
  }

  retarget() {
    this.tx = this.bx + (Math.random() - 0.5) * this.wanderRadius * 2;
    this.ty = this.by + (Math.random() - 0.5) * this.wanderRadius * 2;
  }

  tick(tradeTexts, _wanderRadius, spinSpeed) {
    super.tick(tradeTexts, this.wanderRadius, spinSpeed || 0.09);
  }
}
