import * as PIXI from 'pixi.js';

const W = 780;
const H = 600;

export function drawPit(app) {
  const RED = 0xff3333;
  const GREEN = 0x00ff00;
  const ORG = 0xff8c00;

  const bg = new PIXI.Graphics();
  bg.beginFill(0x060202);
  bg.drawRect(0, 0, W, H);
  for (let tx = 0; tx < W; tx += 28) {
    for (let ty = 140; ty < H - 44; ty += 28) {
      const even = (Math.floor(tx / 28) + Math.floor(ty / 28)) % 2 === 0;
      bg.beginFill(even ? 0x0d0404 : 0x090202);
      bg.drawRect(tx, ty, 28, 28);
    }
  }
  bg.beginFill(0x1a1010, 0.45);
  for (let i = 0; i < 28; i++) {
    bg.drawEllipse(
      28 + Math.floor(Math.random() * (W - 56)),
      148 + Math.floor(Math.random() * (H - 210)),
      4 + Math.floor(Math.random() * 20),
      3 + Math.floor(Math.random() * 10)
    );
  }
  [50, W - 72].forEach((tx) => {
    bg.beginFill(0x1a0808);
    bg.lineStyle(1, RED, 0.3);
    bg.drawCircle(tx, H - 90, 22);
    bg.lineStyle(0);
    bg.beginFill(0x0a0404);
    bg.drawCircle(tx, H - 90, 14);
  });
  app.stage.addChild(bg);

  const sm = new PIXI.Graphics();
  sm.beginFill(0x050101);
  sm.drawRect(0, 0, W, 136);
  sm.lineStyle(1, 0x1a0000, 0.5);
  sm.moveTo(0, 136); sm.lineTo(W, 136);
  sm.lineStyle(0);

  const screenRects = [
    { x: 8, y: 4, w: 138, h: 126, color: RED },
    { x: 154, y: 4, w: 138, h: 126, color: GREEN },
    { x: 300, y: 4, w: 138, h: 126, color: RED },
    { x: 446, y: 4, w: 138, h: 126, color: GREEN },
    { x: 592, y: 4, w: 180, h: 126, color: ORG },
  ];
  const sLbls = ['SELL -2.1%', 'BUY +4.3%', 'SELL -0.8%', 'BUY +1.9%', 'HOLD'];

  screenRects.forEach((s, si) => {
    sm.beginFill(0x040101);
    sm.drawRect(s.x, s.y, s.w, s.h);
    sm.lineStyle(1.5, s.color, 0.6);
    sm.drawRect(s.x, s.y, s.w, s.h);
    sm.lineStyle(0);
    sm.beginFill(s.color, 0.04);
    sm.drawRect(s.x + 2, s.y + 2, s.w - 4, s.h - 4);
    const barHeights = [20, 30, 14, 42, 26, 48, 36, 54, 26, 60];
    barHeights.forEach((bh, i) => {
      sm.beginFill(s.color, 0.45);
      sm.drawRect(s.x + 8 + i * 14, s.y + s.h - 8 - bh, 10, bh);
    });
    sm.beginFill(s.color, 0.9);
    sm.drawCircle(s.x + s.w - 12, s.y + 12, 5);

    const lbl = new PIXI.Text(sLbls[si], {
      fontFamily: '"Press Start 2P", monospace',
      fontSize: 8,
      fill: s.color,
      resolution: 2,
    });
    lbl.x = s.x + 8;
    lbl.y = s.y + 10;
    app.stage.addChild(lbl);
  });
  app.stage.addChild(sm);

  const f = new PIXI.Graphics();
  const deskRows = [
    [{ x: 10, y: 144 }, { x: 166, y: 144 }, { x: 322, y: 144 }, { x: 478, y: 144 }, { x: 634, y: 144 }],
    [{ x: 60, y: 296 }, { x: 248, y: 296 }, { x: 436, y: 296 }, { x: 624, y: 296 }],
    [{ x: 26, y: 448 }, { x: 222, y: 448 }, { x: 418, y: 448 }, { x: 598, y: 448 }],
  ];
  const seatPositions = [];

  deskRows.forEach((row) => {
    row.forEach((d) => {
      f.beginFill(0x120404);
      f.lineStyle(1, RED, 0.2);
      f.drawRect(d.x, d.y, 132, 50);
      f.lineStyle(0);
      f.beginFill(0x030101);
      f.lineStyle(1, RED, 0.3);
      f.drawRect(d.x + 6, d.y + 6, 56, 34);
      f.lineStyle(0);
      const ledOn = Math.random() > 0.45;
      f.beginFill(ledOn ? GREEN : RED, 0.9);
      f.drawCircle(d.x + 122, d.y + 8, 4);
      f.beginFill(0x1a0606, 0.65);
      f.drawRect(d.x + 66, d.y + 28, 44, 14);
      seatPositions.push([d.x + 44, d.y + 58]);
    });
  });

  f.beginFill(0xff0000);
  f.lineStyle(3, 0x660000);
  f.drawCircle(W - 32, H - 60, 22);
  f.lineStyle(0);
  f.beginFill(0xcc0000);
  f.drawCircle(W - 32, H - 60, 14);
  app.stage.addChild(f);

  const timerText = new PIXI.Text('09:24:38', {
    fontFamily: '"Press Start 2P", monospace',
    fontSize: 14,
    fill: RED,
    resolution: 2,
  });
  timerText.x = W - 172;
  timerText.y = H - 82;
  app.stage.addChild(timerText);

  return { seatPositions: seatPositions.slice(0, 13), screenRects, timerText };
}
