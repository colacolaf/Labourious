import * as PIXI from 'pixi.js';

export class ChaosSymbol {
  constructor(app, cx, cy, symbol, color) {
    this.angle = Math.random() * Math.PI * 2;
    this.r = 14 + Math.random() * 8;
    this.speed = (Math.random() - 0.5) * 0.06 + 0.045;
    this.life = 100 + Math.random() * 150;

    this.text = new PIXI.Text(symbol, {
      fontFamily: '"Press Start 2P", monospace',
      fontSize: 5,
      fill: color,
      resolution: 2,
    });
    this.text.anchor.set(0.5);
    app.stage.addChild(this.text);
  }

  tick(agentX, agentY) {
    this.angle += this.speed;
    this.text.x = agentX + Math.cos(this.angle) * this.r;
    this.text.y = agentY + Math.sin(this.angle) * this.r * 0.55;
    this.life--;
    this.text.alpha = this.life < 25 ? this.life / 25 : 1;
    return this.life > 0;
  }

  destroy(app) {
    app.stage.removeChild(this.text);
    this.text.destroy();
  }
}
