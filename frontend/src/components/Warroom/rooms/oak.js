import * as PIXI from 'pixi.js';

const W = 780;
const H = 600;

export function drawOak(app) {
  const AMBER = 0xcc8833;
  const COPPER = 0xb87333;

  const bg = new PIXI.Graphics();
  bg.beginFill(0x2a3840);
  bg.drawRect(0, 0, W, 38);
  [124, 390, 656].forEach((lx) => {
    bg.beginFill(0xfff8e0, 0.15);
    bg.drawEllipse(lx, 18, 78, 18);
    bg.beginFill(0xfff8e0, 0.22);
    bg.drawRect(lx - 50, 12, 100, 12);
  });
  bg.beginFill(0x2e2014);
  bg.drawRect(0, 0, 28, H);
  bg.beginFill(0x2e2014);
  bg.drawRect(W - 28, 0, 28, H);
  bg.lineStyle(1, AMBER, 0.07);
  for (let y = 50; y < H; y += 60) {
    bg.moveTo(0, y); bg.lineTo(28, y);
    bg.moveTo(W - 28, y); bg.lineTo(W, y);
  }
  bg.lineStyle(0);
  for (let y = 38; y < H - 38; y += 30) {
    bg.beginFill(0x2a1c0a + (Math.floor(y / 30) % 4) * 0x020200);
    bg.drawRect(28, y, W - 56, 30);
  }
  bg.lineStyle(1, 0x1a1008, 0.6);
  for (let y = 38; y < H - 38; y += 30) {
    bg.moveTo(28, y); bg.lineTo(W - 28, y);
  }
  bg.lineStyle(0);
  app.stage.addChild(bg);

  const f = new PIXI.Graphics();
  [40, 288, 536].forEach((wx) => {
    f.beginFill(0x2e2e28);
    f.lineStyle(1, AMBER, 0.3);
    f.drawRect(wx, 40, 190, 76);
    f.lineStyle(0);
    f.lineStyle(1.5, AMBER, 0.16);
    for (let i = 0; i < 4; i++) {
      f.moveTo(wx + 12 + i * 22, 58);
      f.lineTo(wx + 50 + i * 22 + 28, 58 + 38 * Math.random());
    }
    const pp = [wx + 10, 102, wx + 34, 88, wx + 58, 94, wx + 82, 72, wx + 112, 80, wx + 140, 64, wx + 174, 76];
    for (let i = 0; i < pp.length - 2; i += 2) {
      f.moveTo(pp[i], pp[i + 1]);
      f.lineTo(pp[i + 2], pp[i + 3]);
    }
    f.lineStyle(0);
  });

  [[W - 26, 140], [W - 26, 314]].forEach(([cx, cy]) => {
    f.beginFill(0x1e1c14);
    f.lineStyle(1, AMBER, 0.3);
    f.drawRect(cx, cy, 90, 66);
    f.lineStyle(0);
    f.lineStyle(1, COPPER, 0.4);
    const cp = [cx + 8, cy + 56, cx + 22, cy + 40, cx + 40, cy + 48, cx + 58, cy + 28, cx + 74, cy + 36, cx + 86, cy + 18];
    for (let i = 0; i < cp.length - 2; i += 2) {
      f.moveTo(cp[i], cp[i + 1]);
      f.lineTo(cp[i + 2], cp[i + 3]);
    }
    f.lineStyle(0);
  });

  const deskDefs = [
    { x: 38, y: 160, w: 172, h: 66 },
    { x: 38, y: 320, w: 172, h: 66 },
    { x: 262, y: 214, w: 172, h: 66 },
    { x: 262, y: 388, w: 172, h: 66 },
    { x: 456, y: 160, w: 140, h: 66 },
    { x: 456, y: 320, w: 140, h: 66 },
  ];
  const seatPositions = deskDefs.map(d => [d.x + d.w / 2 - 20, d.y + d.h + 8]);

  deskDefs.forEach((d) => {
    f.beginFill(0x2a1c0a);
    f.lineStyle(1, AMBER, 0.55);
    f.drawRect(d.x, d.y, d.w, d.h);
    f.lineStyle(0);
    f.beginFill(0x060402);
    f.lineStyle(1, AMBER, 0.3);
    f.drawRect(d.x + 10, d.y + 10, 46, 38);
    f.lineStyle(0);
    f.beginFill(0x030200);
    f.drawRect(d.x + 12, d.y + 12, 42, 34);
    f.beginFill(AMBER, 0.3);
    for (let i = 0; i < 3; i++) f.drawRect(d.x + 16, d.y + 16 + i * 8, 28, 3);
    if (d.w > 150) {
      f.beginFill(0x060402);
      f.lineStyle(1, AMBER, 0.3);
      f.drawRect(d.x + 72, d.y + 10, 46, 38);
      f.lineStyle(0);
      f.beginFill(0x030200);
      f.drawRect(d.x + 74, d.y + 12, 42, 34);
      f.beginFill(AMBER, 0.3);
      for (let i = 0; i < 3; i++) f.drawRect(d.x + 78, d.y + 16 + i * 8, 28, 3);
    }
    f.beginFill(0x4a3020);
    f.drawCircle(d.x + d.w - 16, d.y + d.h - 16, 8);
    f.beginFill(0x2a1a0a);
    f.drawCircle(d.x + d.w - 16, d.y + d.h - 16, 5);
    f.beginFill(0xcc6600, 0.07);
    f.drawEllipse(d.x + d.w * 0.4, d.y + d.h * 0.5, 60, 34);
  });

  f.beginFill(0x1e1008);
  f.lineStyle(1, AMBER, 0.2);
  f.drawRect(280, H - 54, 220, 54);
  f.lineStyle(0);
  f.beginFill(0x2a1810);
  f.drawRect(284, H - 50, 212, 38);
  [288, 372].forEach((cx) => {
    f.beginFill(0x321e0e);
    f.drawRoundedRect(cx, H - 48, 82, 28, 8);
  });

  app.stage.addChild(f);

  return { seatPositions };
}
