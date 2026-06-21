import * as PIXI from 'pixi.js';

const W = 780;
const H = 600;
const SKY = Math.floor(H * 0.35);

function checker(g, x, y, w, h, c1, c2, sz) {
  for (let tx = x; tx < x + w; tx += sz) {
    for (let ty = y; ty < y + h; ty += sz) {
      const even = (Math.floor((tx - x) / sz) + Math.floor((ty - y) / sz)) % 2 === 0;
      g.beginFill(even ? c1 : c2);
      g.drawRect(tx, ty, Math.min(sz, x + w - tx), Math.min(sz, y + h - ty));
    }
  }
}

export function drawBloomberg(app) {
  const BLUE = 0x4a7eba;
  const GOLD = 0xd4af37;

  const sky = new PIXI.Graphics();
  for (let i = 0; i < SKY; i += 4) {
    const t = i / SKY;
    const r = Math.round(0xb0 + (0xe8 - 0xb0) * t);
    const gr = Math.round(0xcc + (0xf0 - 0xcc) * t);
    const b2 = Math.round(0xf0 + (0xf8 - 0xf0) * t);
    sky.beginFill((r << 16) | (gr << 8) | b2, 0.95);
    sky.drawRect(0, i, W, 4);
  }
  [[55, 18, 170, 32], [300, 10, 210, 36], [600, 22, 155, 30]].forEach(([cx, cy, cw, ch]) => {
    sky.beginFill(0xffffff, 0.7);
    sky.drawRoundedRect(cx, cy, cw, ch, ch / 2);
    sky.beginFill(0xffffff, 0.5);
    sky.drawRoundedRect(cx + 20, cy - 10, cw * 0.6, ch, ch / 2);
  });
  const blds = [
    [0, 30, 55, SKY - 30], [58, 16, 72, SKY - 16], [134, 48, 42, SKY - 48],
    [180, 10, 78, SKY - 10], [262, 44, 55, SKY - 44], [322, 20, 68, SKY - 20],
    [395, 58, 45, SKY - 58], [444, 12, 78, SKY - 12], [526, 50, 50, SKY - 50],
    [580, 28, 62, SKY - 28], [646, 8, 72, SKY - 8], [722, 42, 58, SKY - 42],
  ];
  blds.forEach(([bx, by, bw, bh]) => {
    const lum = 0x4a6880 + (Math.floor(Math.random() * 0x101820));
    sky.beginFill(lum);
    sky.drawRect(bx, by, bw, bh);
    sky.beginFill(0xd0e8f8, 0.5);
    for (let wy = by + 10; wy < by + bh - 10; wy += 16) {
      for (let wx = bx + 8; wx < bx + bw - 6; wx += 14) {
        if (Math.random() > 0.35) sky.drawRect(wx, wy, 6, 8);
      }
    }
  });
  sky.beginFill(0xd0dcea);
  sky.drawRect(0, SKY, W, 16);
  checker(sky, 0, SKY + 16, W, H - SKY - 36, 0xeef2f8, 0xe4ecf4, 44);
  app.stage.addChild(sky);

  const f = new PIXI.Graphics();

  const desks = [
    { x: 34, y: SKY + 54, w: 200, h: 62 },
    { x: 34, y: SKY + 170, w: 200, h: 62 },
    { x: 278, y: SKY + 104, w: 195, h: 76 },
    { x: 512, y: SKY + 54, w: 238, h: 180 },
    { x: 462, y: SKY + 48, w: 44, h: 90 },
  ];

  desks.slice(0, 4).forEach((d) => {
    f.beginFill(0xc8a870);
    f.lineStyle(2, GOLD, 0.6);
    f.drawRect(d.x, d.y, d.w, d.h);
    f.lineStyle(0);
    const monSlots = d.w > 190 ? [20, 70, 120] : [20, 70];
    monSlots.forEach((ox) => {
      f.beginFill(0xa08040);
      f.drawRect(d.x + ox - 2, d.y + 8, 46, 38);
      f.beginFill(0x1a2a1a);
      f.drawRect(d.x + ox, d.y + 10, 42, 34);
      f.beginFill(GOLD, 0.5);
      for (let i = 0; i < 4; i++) f.drawRect(d.x + ox + 4, d.y + 14 + i * 7, 30, 3);
    });
    f.beginFill(0xf8f0e0, 0.8);
    f.drawRect(d.x + 4, d.y + d.h - 26, 52, 22);
  });

  f.beginFill(0xccd4e0);
  f.lineStyle(1, BLUE, 0.3);
  f.drawRect(desks[4].x, desks[4].y, desks[4].w, desks[4].h);
  f.lineStyle(1, BLUE, 0.15);
  f.moveTo(desks[4].x, desks[4].y + desks[4].h * 0.4);
  f.lineTo(desks[4].x + desks[4].w, desks[4].y + desks[4].h * 0.4);
  f.moveTo(desks[4].x, desks[4].y + desks[4].h * 0.7);
  f.lineTo(desks[4].x + desks[4].w, desks[4].y + desks[4].h * 0.7);
  f.lineStyle(0);

  [[240, SKY + 58], [472, SKY + 240], [22, SKY + 290], [752, SKY + 290]].forEach(([px, py]) => {
    f.beginFill(0x2a5a10); f.drawCircle(px, py, 24);
    f.beginFill(0x3a8018); f.drawCircle(px - 6, py - 8, 16);
    f.beginFill(0x4aaa22); f.drawCircle(px + 6, py - 14, 12);
    f.beginFill(0x5a5030); f.drawRect(px - 14, py + 16, 28, 16);
  });

  app.stage.addChild(f);

  const bounds = { x0: 38, y0: SKY + 28, x1: W - 38, y1: H - 44 };

  const spawnPoints = [
    [22, SKY + 134],
    [22, SKY + 260],
    [234, SKY + 260],
    [234, SKY + 134],
    [400, SKY + 194],
    [400, SKY + 270],
    [750, SKY + 280],
  ];

  return { desks, bounds, spawnPoints };
}
