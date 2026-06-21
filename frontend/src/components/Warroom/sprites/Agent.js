import * as PIXI from 'pixi.js';

export class Agent {
  constructor(app, x, y, bodyColor, headColor, borderColor, vestColor = null) {
    this.app = app;
    this.x = x;
    this.y = y;
    this.tx = x;
    this.ty = y;
    this.spd = 0.35;
    this.pause = Math.random() * 60;
    this.stepF = 0;
    this.legPh = 0;
    this.dir = 1;
    this.tradeT = 150 + Math.random() * 300;
    this.spinA = 0;
    this.spinning = false;
    this.spinT = 0;
    this.id = null;
    this._ring = null;

    this.c = new PIXI.Container();
    app.stage.addChild(this.c);

    const g = new PIXI.Graphics();
    g.beginFill(0x000000, 0.15);
    g.drawEllipse(7, 15, 5, 2);
    g.beginFill(bodyColor);
    g.lineStyle(1.5, borderColor, 0.9);
    g.drawEllipse(7, 9, 5, 7);
    g.lineStyle(0);
    if (vestColor) {
      g.beginFill(vestColor, 0.8);
      g.drawRect(4, 6, 6, 5);
    }
    g.beginFill(headColor);
    g.lineStyle(1, borderColor, 0.8);
    g.drawCircle(7, 3, 3.5);
    g.lineStyle(0);
    g.beginFill(0x000000, 0.75);
    g.drawCircle(5.5, 3, 0.9);
    g.drawCircle(8.5, 3, 0.9);
    g.beginFill(0x000000, 0.55);
    g.drawRect(3.5, 1.5, 8, 1.5);
    this.c.addChild(g);

    this.ll = new PIXI.Graphics();
    this.rl = new PIXI.Graphics();
    this.ll.beginFill(borderColor, 0.6);
    this.ll.drawCircle(5, 16, 2);
    this.rl.beginFill(borderColor, 0.6);
    this.rl.drawCircle(9, 16, 2);
    this.c.addChild(this.ll);
    this.c.addChild(this.rl);

    this.spinner = new PIXI.Graphics();
    this.spinner.lineStyle(2, 0xffffff, 0.9);
    this.spinner.arc(7, -6, 4, 0, Math.PI * 1.5);
    this.spinner.visible = false;
    this.c.addChild(this.spinner);

    this.ttxt = new PIXI.Text('', {
      fontFamily: '"Press Start 2P", monospace',
      fontSize: 5,
      fill: 0x00ff88,
      resolution: 2,
    });
    this.ttxt.anchor.set(0.5, 1);
    this.ttxt.x = 7;
    this.ttxt.y = -9;
    this.ttxt.visible = false;
    this.c.addChild(this.ttxt);
    this.ttxtLife = 0;

    this.flash = new PIXI.Graphics();
    this.flashLife = 0;
    this.flashCol = 0x00ff88;
    this.c.addChild(this.flash);

    this.c.interactive = true;
    this.c.buttonMode = true;
    this.c.on('pointerdown', () => this._toggleRing());
  }

  _toggleRing() {
    if (this._ring) {
      this.c.removeChild(this._ring);
      this._ring.destroy();
      this._ring = null;
    } else {
      this._ring = new PIXI.Graphics();
      this._ring.lineStyle(2, 0xffffff, 0.7);
      this._ring.drawCircle(7, 8, 11);
      this.c.addChildAt(this._ring, 0);
    }
  }

  onTrade(symbol, action, pnl) {
    const up = action === 'BUY' || pnl >= 0;
    const col = up ? 0x00ff88 : 0xff4444;
    this.ttxt.text = `${action} ${symbol}`;
    this.ttxt.style.fill = col;
    this.ttxt.visible = true;
    this.ttxtLife = 150;
    this.ttxt.alpha = 1;
    this.flashCol = col;
    this.flashLife = 22;
  }

  onProcessing() {
    this.spinning = true;
    this.spinT = 90;
    this.spinner.visible = true;
  }

  retarget() {
    this.tx = this.x;
    this.ty = this.y;
  }

  tick(tradeTexts, wanderRadius = 0, spinSpeed = 0.1) {
    if (this.pause > 0) { this.pause--; return; }

    const dx = this.tx - this.x;
    const dy = this.ty - this.y;
    const d = Math.sqrt(dx * dx + dy * dy);

    if (d < 2) {
      this.pause = 40 + Math.random() * 80;
      this.retarget();
    } else {
      this.x += (dx / d) * this.spd;
      this.y += (dy / d) * this.spd;
      this.dir = dx > 0 ? 1 : -1;

      const cyclePeriod = wanderRadius ? 14 : 6;
      this.stepF++;
      if (this.stepF % cyclePeriod === 0) this.legPh = 1 - this.legPh;
      const legOffset = wanderRadius ? 0.8 : 1.5;
      this.ll.y = this.legPh === 0 ? -legOffset : legOffset;
      this.rl.y = this.legPh === 0 ? legOffset : -legOffset;
    }

    this.c.scale.x = this.dir < 0 ? -1 : 1;
    this.c.x = this.x + (this.dir < 0 ? 14 : 0);
    this.c.y = this.y;

    if (this.spinning) {
      this.spinA += spinSpeed;
      this.spinner.rotation = this.spinA;
      this.spinT--;
      if (this.spinT <= 0) {
        this.spinning = false;
        this.spinner.visible = false;
      }
    }

    if (this.ttxtLife > 0) {
      this.ttxtLife--;
      if (this.ttxtLife < 30) this.ttxt.alpha = this.ttxtLife / 30;
      if (this.ttxtLife === 0) {
        this.ttxt.visible = false;
        this.ttxt.alpha = 1;
      }
    }

    if (this.flashLife > 0) {
      this.flashLife--;
      this.flash.clear();
      this.flash.beginFill(this.flashCol, (this.flashLife / 22) * 0.4);
      this.flash.drawEllipse(7, 8, 7, 10);
    }

    if (window.__LABOURIOUS_DEMO__ && tradeTexts && tradeTexts.length > 0) {
      this.tradeT--;
      if (this.tradeT <= 0) {
        const sym = tradeTexts[Math.floor(Math.random() * tradeTexts.length)];
        const action = Math.random() > 0.5 ? 'BUY' : 'SELL';
        this.onTrade(sym, action, action === 'BUY' ? 1 : -1);
        if (Math.random() > 0.6) this.onProcessing();
        this.tradeT = (wanderRadius ? 250 : 70) + Math.random() * 200;
      }
    }
  }

  destroy() {
    this.app.stage.removeChild(this.c);
    this.c.destroy({ children: true });
  }
}
