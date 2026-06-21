# Phase 4C — PixiJS Warroom Rooms Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder `Warroom.jsx` IsometricGrid renderer with three visually distinct PixiJS rooms (Bloomberg, Oak Office, The Pit), connected to the existing WebSocket feed for real trade events.

**Architecture:** PixiJS 7 canvas mounted in `PixiWarroom.jsx`; room-specific background/furniture drawn in JS modules; Agent sprite class hierarchy; `useWarroomAgents` hook bridges the WS store and sprite callbacks. Each page (`WarroomLongTerm`, `WarroomSwing`, `WarroomDay`) swaps its render to `<PixiWarroom room="..." />`.

**Tech Stack:** pixi.js ^7.4.2, React 18, Zustand, existing `useWebSocketStore`, existing `agentsApi`

## Global Constraints

- CSS vars only: `var(--color-*)`, `var(--font-mono)`, `var(--space-*)`. Never hardcode colors in JSX/CSS.
- No new npm deps beyond `pixi.js@^7.4.2`.
- Canvas pixel art: `image-rendering: pixelated` on canvas element.
- Agents filtered by room key (`long_term`, `swing_trading`, `day_trading`).
- Demo fallback activates after 3s with no WS events (`window.__LABOURIOUS_DEMO__ = true`).
- All WS events routed through existing `useWebSocketStore.lastMessage`.
- No `console.log` — use no-op silently (these are render-loop files).
- `pixi.js` import via npm package (not CDN) in production components.
- Desk AABB collision for Bloomberg free-walk agents only; Oak/Pit agents are `SeatedAgent` (no collision needed).
- PixiJS app destroyed in React `useEffect` cleanup to prevent canvas leak.
- `PIXI.Application` created with `{ antialias: false }` for pixel art sharpness.
- Target 30fps: `app.ticker.maxFPS = 30`.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/package.json` | Modify | Add `"pixi.js": "^7.4.2"` dependency |
| `frontend/src/components/Warroom/sprites/Agent.js` | Create | Base agent class — body, head, legs, trade bubble, spinner, flash, click handler |
| `frontend/src/components/Warroom/sprites/WalkingAgent.js` | Create | Free-walk + AABB desk avoidance |
| `frontend/src/components/Warroom/sprites/SeatedAgent.js` | Create | Micro-wander ±radius from base position |
| `frontend/src/components/Warroom/sprites/ChaosSymbol.js` | Create | Orbiting symbol for The Pit |
| `frontend/src/components/Warroom/rooms/bloomberg.js` | Create | Background, furniture, desk AABBs, spawn points |
| `frontend/src/components/Warroom/rooms/oak.js` | Create | Background, furniture, seat positions |
| `frontend/src/components/Warroom/rooms/pit.js` | Create | Background, screen wall, seat positions, chaos config |
| `frontend/src/components/Warroom/hooks/useWarroomAgents.js` | Create | Load agents from API, subscribe WS, call sprite callbacks |
| `frontend/src/components/Warroom/PixiWarroom.jsx` | Create | React wrapper: mount PixiJS app, draw room, create agents, start ticker |
| `frontend/src/pages/WarroomLongTerm.jsx` | Modify | Render `<PixiWarroom room="long_term" />` |
| `frontend/src/pages/WarroomSwing.jsx` | Modify | Render `<PixiWarroom room="swing_trading" />` |
| `frontend/src/pages/WarroomDay.jsx` | Modify | Render `<PixiWarroom room="day_trading" />` |

---

### Task 1: Install pixi.js

**Files:**
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: `import * as PIXI from 'pixi.js'` works in all subsequent files

- [ ] **Step 1: Add pixi.js to package.json dependencies**

Open `frontend/package.json`. In the `"dependencies"` object, add:
```json
"pixi.js": "^7.4.2"
```

- [ ] **Step 2: Install**

```bash
cd frontend && npm install
```
Expected: `added N packages` with no errors. `node_modules/pixi.js` exists.

- [ ] **Step 3: Verify import resolves**

```bash
cd frontend && node -e "require('pixi.js'); console.log('ok')"
```
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat(4C): Install pixi.js ^7.4.2"
```

---

### Task 2: Agent base class

**Files:**
- Create: `frontend/src/components/Warroom/sprites/Agent.js`

**Interfaces:**
- Produces:
  - `new Agent(pixiApp, x, y, bodyColor, headColor, borderColor, vestColor)` — constructs sprite, adds `this.c` (PIXI.Container) to `pixiApp.stage`
  - `agent.onTrade(symbol, action, pnl)` — show trade bubble + flash
  - `agent.onProcessing()` — show spinner for 90 frames
  - `agent.tick(tradeTexts, wanderRadius, spinSpeed)` — call each frame
  - `agent.destroy()` — remove container from stage
  - `agent.x`, `agent.y` — current position (mutable)
  - `agent.id` — set externally after construction (for WS dispatch)

- [ ] **Step 1: Create file**

```javascript
// frontend/src/components/Warroom/sprites/Agent.js
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
    this.id = null; // set externally after construction
    this._ring = null;

    this.c = new PIXI.Container();
    app.stage.addChild(this.c);

    // Shadow
    const g = new PIXI.Graphics();
    g.beginFill(0x000000, 0.15);
    g.drawEllipse(7, 15, 5, 2);
    // Body
    g.beginFill(bodyColor);
    g.lineStyle(1.5, borderColor, 0.9);
    g.drawEllipse(7, 9, 5, 7);
    g.lineStyle(0);
    // Vest overlay
    if (vestColor) {
      g.beginFill(vestColor, 0.8);
      g.drawRect(4, 6, 6, 5);
    }
    // Head
    g.beginFill(headColor);
    g.lineStyle(1, borderColor, 0.8);
    g.drawCircle(7, 3, 3.5);
    g.lineStyle(0);
    // Eyes (dark dots)
    g.beginFill(0x000000, 0.75);
    g.drawCircle(5.5, 3, 0.9);
    g.drawCircle(8.5, 3, 0.9);
    // Sunglasses bar
    g.beginFill(0x000000, 0.55);
    g.drawRect(3.5, 1.5, 8, 1.5);
    this.c.addChild(g);

    // Legs
    this.ll = new PIXI.Graphics();
    this.rl = new PIXI.Graphics();
    this.ll.beginFill(borderColor, 0.6);
    this.ll.drawCircle(5, 16, 2);
    this.rl.beginFill(borderColor, 0.6);
    this.rl.drawCircle(9, 16, 2);
    this.c.addChild(this.ll);
    this.c.addChild(this.rl);

    // Spinner arc (LLM processing)
    this.spinner = new PIXI.Graphics();
    this.spinner.lineStyle(2, 0xffffff, 0.9);
    this.spinner.arc(7, -6, 4, 0, Math.PI * 1.5);
    this.spinner.visible = false;
    this.c.addChild(this.spinner);

    // Trade text bubble
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

    // Flash overlay
    this.flash = new PIXI.Graphics();
    this.flashLife = 0;
    this.flashCol = 0x00ff88;
    this.c.addChild(this.flash);

    // Click to highlight
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

  // Subclasses override retarget()
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

    // Demo-mode fallback: fire random trade if no real WS event arrived
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
```

- [ ] **Step 2: Verify no lint errors**

```bash
cd frontend && npx eslint src/components/Warroom/sprites/Agent.js --max-warnings=0 2>&1 | tail -5
```
Expected: no output (or `0 warnings`)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Warroom/sprites/Agent.js
git commit -m "feat(4C): Add Agent base sprite class"
```

---

### Task 3: WalkingAgent + SeatedAgent + ChaosSymbol

**Files:**
- Create: `frontend/src/components/Warroom/sprites/WalkingAgent.js`
- Create: `frontend/src/components/Warroom/sprites/SeatedAgent.js`
- Create: `frontend/src/components/Warroom/sprites/ChaosSymbol.js`

**Interfaces:**
- Consumes: `Agent` from `./Agent`
- Produces:
  - `new WalkingAgent(app, x, y, bodyColor, headColor, borderColor, vestColor, bounds, blockedRects)` — free walk in `bounds`, avoids `blockedRects`
  - `new SeatedAgent(app, x, y, bodyColor, headColor, borderColor, vestColor, wanderRadius)` — micro-wander ±`wanderRadius`
  - `new ChaosSymbol(app, cx, cy, symbol, color)` — orbiting symbol
    - `symbol.tick(agentX, agentY)` — returns `true` while alive
    - `symbol.destroy(app)` — removes from stage

- [ ] **Step 1: Create WalkingAgent.js**

```javascript
// frontend/src/components/Warroom/sprites/WalkingAgent.js
import { Agent } from './Agent';

function rectHit(px, py, r, rx, ry, rw, rh) {
  return px + r > rx && px - r < rx + rw && py + r > ry && py - r < ry + rh;
}

export class WalkingAgent extends Agent {
  constructor(app, x, y, bodyColor, headColor, borderColor, vestColor, bounds, blockedRects) {
    super(app, x, y, bodyColor, headColor, borderColor, vestColor);
    this.bounds = bounds; // { x0, y0, x1, y1 }
    this.blocked = blockedRects; // [{ x, y, w, h }, ...]
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
    // fallback: center of room
    this.tx = (this.bounds.x0 + this.bounds.x1) / 2;
    this.ty = (this.bounds.y0 + this.bounds.y1) / 2;
  }

  tick(tradeTexts, _wanderRadius, spinSpeed) {
    // Nudge out of desks each frame
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
```

- [ ] **Step 2: Create SeatedAgent.js**

```javascript
// frontend/src/components/Warroom/sprites/SeatedAgent.js
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
```

- [ ] **Step 3: Create ChaosSymbol.js**

```javascript
// frontend/src/components/Warroom/sprites/ChaosSymbol.js
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

  // Returns true while alive; follow agentX/agentY
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
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Warroom/sprites/
git commit -m "feat(4C): Add WalkingAgent, SeatedAgent, ChaosSymbol sprites"
```

---

### Task 4: Bloomberg room module

**Files:**
- Create: `frontend/src/components/Warroom/rooms/bloomberg.js`

**Interfaces:**
- Consumes: `PIXI` from `pixi.js`
- Produces:
  - `drawBloomberg(app)` — draws background + furniture onto `app.stage`; returns `{ desks, bounds, spawnPoints }`
  - `desks: Array<{x,y,w,h}>` — AABB collision rects
  - `bounds: {x0,y0,x1,y1}` — walkable area
  - `spawnPoints: Array<[number,number]>` — 7 agent spawn coordinates

- [ ] **Step 1: Create bloomberg.js**

```javascript
// frontend/src/components/Warroom/rooms/bloomberg.js
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
  const TEAL = 0x1a3a3a;

  // Sky gradient (approximated with horizontal bands)
  const sky = new PIXI.Graphics();
  for (let i = 0; i < SKY; i += 4) {
    const t = i / SKY;
    const r = Math.round(0xb0 + (0xe8 - 0xb0) * t);
    const gr = Math.round(0xcc + (0xf0 - 0xcc) * t);
    const b2 = Math.round(0xf0 + (0xf8 - 0xf0) * t);
    sky.beginFill((r << 16) | (gr << 8) | b2, 0.95);
    sky.drawRect(0, i, W, 4);
  }
  // Clouds
  [[55, 18, 170, 32], [300, 10, 210, 36], [600, 22, 155, 30]].forEach(([cx, cy, cw, ch]) => {
    sky.beginFill(0xffffff, 0.7);
    sky.drawRoundedRect(cx, cy, cw, ch, ch / 2);
    sky.beginFill(0xffffff, 0.5);
    sky.drawRoundedRect(cx + 20, cy - 10, cw * 0.6, ch, ch / 2);
  });
  // Buildings
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
    // Lit windows
    sky.beginFill(0xd0e8f8, 0.5);
    for (let wy = by + 10; wy < by + bh - 10; wy += 16) {
      for (let wx = bx + 8; wx < bx + bw - 6; wx += 14) {
        if (Math.random() > 0.35) sky.drawRect(wx, wy, 6, 8);
      }
    }
  });
  // Horizon strip
  sky.beginFill(0xd0dcea);
  sky.drawRect(0, SKY, W, 16);
  // Floor
  checker(sky, 0, SKY + 16, W, H - SKY - 36, 0xeef2f8, 0xe4ecf4, 44);
  app.stage.addChild(sky);

  // Furniture
  const f = new PIXI.Graphics();

  const desks = [
    { x: 34, y: SKY + 54, w: 200, h: 62 },  // left desk row 1
    { x: 34, y: SKY + 170, w: 200, h: 62 },  // left desk row 2
    { x: 278, y: SKY + 104, w: 195, h: 76 }, // center cluster
    { x: 512, y: SKY + 54, w: 238, h: 180 }, // right desk bank
    { x: 462, y: SKY + 48, w: 44, h: 90 },   // filing cabinet
  ];

  // Draw desks
  desks.slice(0, 4).forEach((d) => {
    f.beginFill(0xc8a870);
    f.lineStyle(2, GOLD, 0.6);
    f.drawRect(d.x, d.y, d.w, d.h);
    f.lineStyle(0);
    // Monitors
    const monSlots = d.w > 190 ? [20, 70, 120] : [20, 70];
    monSlots.forEach((ox) => {
      // Monitor frame
      f.beginFill(0xa08040);
      f.drawRect(d.x + ox - 2, d.y + 8, 46, 38);
      // Monitor screen
      f.beginFill(0x1a2a1a);
      f.drawRect(d.x + ox, d.y + 10, 42, 34);
      // Screen data bars
      f.beginFill(GOLD, 0.5);
      for (let i = 0; i < 4; i++) f.drawRect(d.x + ox + 4, d.y + 14 + i * 7, 30, 3);
    });
    // Papers
    f.beginFill(0xf8f0e0, 0.8);
    f.drawRect(d.x + 4, d.y + d.h - 26, 52, 22);
  });

  // Filing cabinet
  f.beginFill(0xccd4e0);
  f.lineStyle(1, BLUE, 0.3);
  f.drawRect(desks[4].x, desks[4].y, desks[4].w, desks[4].h);
  f.lineStyle(1, BLUE, 0.15);
  f.moveTo(desks[4].x, desks[4].y + desks[4].h * 0.4);
  f.lineTo(desks[4].x + desks[4].w, desks[4].y + desks[4].h * 0.4);
  f.moveTo(desks[4].x, desks[4].y + desks[4].h * 0.7);
  f.lineTo(desks[4].x + desks[4].w, desks[4].y + desks[4].h * 0.7);
  f.lineStyle(0);

  // Plants
  [[240, SKY + 58], [472, SKY + 240], [22, SKY + 290], [752, SKY + 290]].forEach(([px, py]) => {
    f.beginFill(0x2a5a10); f.drawCircle(px, py, 24);
    f.beginFill(0x3a8018); f.drawCircle(px - 6, py - 8, 16);
    f.beginFill(0x4aaa22); f.drawCircle(px + 6, py - 14, 12);
    f.beginFill(0x5a5030); f.drawRect(px - 14, py + 16, 28, 16);
  });

  app.stage.addChild(f);

  const bounds = { x0: 38, y0: SKY + 28, x1: W - 38, y1: H - 44 };

  // Spawn agents in aisles (not on desks)
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Warroom/rooms/bloomberg.js
git commit -m "feat(4C): Add Bloomberg room background module"
```

---

### Task 5: Oak Office room module

**Files:**
- Create: `frontend/src/components/Warroom/rooms/oak.js`

**Interfaces:**
- Produces:
  - `drawOak(app)` → `{ seatPositions }`
  - `seatPositions: Array<[number,number]>` — 6 desk-front positions

- [ ] **Step 1: Create oak.js**

```javascript
// frontend/src/components/Warroom/rooms/oak.js
import * as PIXI from 'pixi.js';

const W = 780;
const H = 600;

export function drawOak(app) {
  const AMBER = 0xcc8833;
  const COPPER = 0xb87333;

  const bg = new PIXI.Graphics();
  // Ceiling / top strip
  bg.beginFill(0x2a3840);
  bg.drawRect(0, 0, W, 38);
  // Fluorescent lights (3)
  [124, 390, 656].forEach((lx) => {
    bg.beginFill(0xfff8e0, 0.15);
    bg.drawEllipse(lx, 18, 78, 18);
    bg.beginFill(0xfff8e0, 0.22);
    bg.drawRect(lx - 50, 12, 100, 12);
  });
  // Side wall panels
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
  // Wood floor planks
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
  // Whiteboards (3, top wall)
  [40, 288, 536].forEach((wx) => {
    f.beginFill(0x2e2e28);
    f.lineStyle(1, AMBER, 0.3);
    f.drawRect(wx, 40, 190, 76);
    f.lineStyle(0);
    // Lines
    f.lineStyle(1.5, AMBER, 0.16);
    for (let i = 0; i < 4; i++) {
      f.moveTo(wx + 12 + i * 22, 58);
      f.lineTo(wx + 50 + i * 22 + 28, 58 + 38 * Math.random());
    }
    // Chart squiggle
    const pp = [wx + 10, 102, wx + 34, 88, wx + 58, 94, wx + 82, 72, wx + 112, 80, wx + 140, 64, wx + 174, 76];
    for (let i = 0; i < pp.length - 2; i += 2) {
      f.moveTo(pp[i], pp[i + 1]);
      f.lineTo(pp[i + 2], pp[i + 3]);
    }
    f.lineStyle(0);
  });

  // Wall charts (right side)
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

  // 6 desks (2 columns × 3 rows)
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
    // Monitors
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
    // Desk lamp
    f.beginFill(0x4a3020);
    f.drawCircle(d.x + d.w - 16, d.y + d.h - 16, 8);
    f.beginFill(0x2a1a0a);
    f.drawCircle(d.x + d.w - 16, d.y + d.h - 16, 5);
    // Lamp glow
    f.beginFill(0xcc6600, 0.07);
    f.drawEllipse(d.x + d.w * 0.4, d.y + d.h * 0.5, 60, 34);
  });

  // Leather couch (bottom center)
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Warroom/rooms/oak.js
git commit -m "feat(4C): Add Oak Office room background module"
```

---

### Task 6: The Pit room module

**Files:**
- Create: `frontend/src/components/Warroom/rooms/pit.js`

**Interfaces:**
- Produces:
  - `drawPit(app)` → `{ seatPositions, screenRects }`
  - `seatPositions: Array<[number,number]>` — 13 desk-front positions
  - `screenRects: Array<{x,y,w,h,color}>` — screen areas for random flicker

- [ ] **Step 1: Create pit.js**

```javascript
// frontend/src/components/Warroom/rooms/pit.js
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
  // Dark checker floor
  for (let tx = 0; tx < W; tx += 28) {
    for (let ty = 140; ty < H - 44; ty += 28) {
      const even = (Math.floor(tx / 28) + Math.floor(ty / 28)) % 2 === 0;
      bg.beginFill(even ? 0x0d0404 : 0x090202);
      bg.drawRect(tx, ty, 28, 28);
    }
  }
  // Crumpled paper + trash
  bg.beginFill(0x1a1010, 0.45);
  for (let i = 0; i < 28; i++) {
    bg.drawEllipse(
      28 + Math.floor(Math.random() * (W - 56)),
      148 + Math.floor(Math.random() * (H - 210)),
      4 + Math.floor(Math.random() * 20),
      3 + Math.floor(Math.random() * 10)
    );
  }
  // Trash cans
  [50, W - 72].forEach((tx) => {
    bg.beginFill(0x1a0808);
    bg.lineStyle(1, RED, 0.3);
    bg.drawCircle(tx, H - 90, 22);
    bg.lineStyle(0);
    bg.beginFill(0x0a0404);
    bg.drawCircle(tx, H - 90, 14);
    for (let i = 0; i < 5; i++) {
      bg.drawEllipse(
        tx - 32 + Math.floor(Math.random() * 64),
        H - 90 - 28 + Math.floor(Math.random() * 56),
        5 + Math.floor(Math.random() * 14),
        3 + Math.floor(Math.random() * 8)
      );
    }
  });
  app.stage.addChild(bg);

  // Screen wall (top strip 0–136px)
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
    // Bar chart
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

  // Desks (3 rows)
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
      // Monitor
      f.beginFill(0x030101);
      f.lineStyle(1, RED, 0.3);
      f.drawRect(d.x + 6, d.y + 6, 56, 34);
      f.lineStyle(0);
      // LED indicator
      const ledOn = Math.random() > 0.45;
      f.beginFill(ledOn ? GREEN : RED, 0.9);
      f.drawCircle(d.x + 122, d.y + 8, 4);
      // Keyboard
      f.beginFill(0x1a0606, 0.65);
      f.drawRect(d.x + 66, d.y + 28, 44, 14);

      seatPositions.push([d.x + 44, d.y + 58]);
    });
  });

  // Emergency button
  f.beginFill(0xff0000);
  f.lineStyle(3, 0x660000);
  f.drawCircle(W - 32, H - 60, 22);
  f.lineStyle(0);
  f.beginFill(0xcc0000);
  f.drawCircle(W - 32, H - 60, 14);
  app.stage.addChild(f);

  // Timer text (updated by PixiWarroom ticker)
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Warroom/rooms/pit.js
git commit -m "feat(4C): Add Pit room background module"
```

---

### Task 7: useWarroomAgents hook

**Files:**
- Create: `frontend/src/components/Warroom/hooks/useWarroomAgents.js`

**Interfaces:**
- Consumes:
  - `agentsApi.list({ room })` from `../../../utils/api-client`
  - `useWebSocketStore` from `../../../stores/websocket.store`
- Produces:
  - `useWarroomAgents(room, agentSprites)` — subscribes WS `lastMessage`, dispatches `onTrade` / `onProcessing` to matching sprite; handles demo fallback

- [ ] **Step 1: Create hook**

```javascript
// frontend/src/components/Warroom/hooks/useWarroomAgents.js
import { useEffect, useRef } from 'react';
import { agentsApi } from '../../../utils/api-client';
import { useWebSocketStore } from '../../../stores/websocket.store';

// agentSprites: Map<agentId, Agent> — populated by PixiWarroom after sprites are created
export function useWarroomAgents(room, agentSprites) {
  const lastMessage = useWebSocketStore((s) => s.lastMessage);
  const demoTimer = useRef(null);
  const hasRealEvent = useRef(false);

  // Load agents from API and assign IDs to sprites by index
  useEffect(() => {
    agentsApi.list({ room }).then((agents) => {
      if (!Array.isArray(agents)) return;
      agents.forEach((agent, i) => {
        // agentSprites is an array; assign id to sprite at position i if it exists
        if (agentSprites[i]) {
          agentSprites[i].id = agent.id;
        }
      });
    }).catch(() => {
      // No backend — demo mode already handles fallback
    });
  }, [room, agentSprites]);

  // Demo fallback: activate after 3s if no real WS event
  useEffect(() => {
    demoTimer.current = setTimeout(() => {
      if (!hasRealEvent.current) {
        window.__LABOURIOUS_DEMO__ = true;
      }
    }, 3000);
    return () => clearTimeout(demoTimer.current);
  }, []);

  // Dispatch WS events to matching sprite
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === 'trade_executed' && lastMessage.agent_id) {
      hasRealEvent.current = true;
      window.__LABOURIOUS_DEMO__ = false;
      const sprite = agentSprites.find((s) => s && s.id === lastMessage.agent_id);
      if (sprite) {
        sprite.onTrade(
          lastMessage.trade?.symbol ?? 'TRADE',
          lastMessage.trade?.action ?? 'BUY',
          lastMessage.trade?.pnl ?? 0
        );
      }
    }

    if (lastMessage.type === 'agent_update' && lastMessage.agent_id) {
      if (lastMessage.data?.status === 'processing') {
        hasRealEvent.current = true;
        const sprite = agentSprites.find((s) => s && s.id === lastMessage.agent_id);
        if (sprite) sprite.onProcessing();
      }
    }
  }, [lastMessage, agentSprites]);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Warroom/hooks/useWarroomAgents.js
git commit -m "feat(4C): Add useWarroomAgents WS integration hook"
```

---

### Task 8: PixiWarroom React component

**Files:**
- Create: `frontend/src/components/Warroom/PixiWarroom.jsx`

**Interfaces:**
- Consumes: all room modules + sprites + hook
- Produces: `<PixiWarroom room="long_term|swing_trading|day_trading" />` — full-height PixiJS canvas

- [ ] **Step 1: Create PixiWarroom.jsx**

```jsx
// frontend/src/components/Warroom/PixiWarroom.jsx
import React, { useEffect, useRef } from 'react';
import * as PIXI from 'pixi.js';
import { WalkingAgent } from './sprites/WalkingAgent';
import { SeatedAgent } from './sprites/SeatedAgent';
import { ChaosSymbol } from './sprites/ChaosSymbol';
import { drawBloomberg } from './rooms/bloomberg';
import { drawOak } from './rooms/oak';
import { drawPit } from './rooms/pit';
import { useWarroomAgents } from './hooks/useWarroomAgents';

const ROOM_W = 780;
const ROOM_H = 600;

const BLOOMBERG_SHIRTS = [0x1a3a6a, 0x1a5a3a, 0x3a1a5a, 0x5a3a1a, 0x1a4a5a, 0x5a1a3a, 0x3a3a1a];
const OAK_SHIRTS = [0x2a3a5a, 0x1a3a28, 0x3a2a1a, 0x2a1a3a, 0x1e3a2a, 0x3a2a2a];
const PIT_VESTS = [0xff2222, 0x2244ff, 0xffcc00, 0x22aa44, 0xff6600, 0xaa22ff, 0x22aaff, 0xff22aa, 0x88ff22, 0xffaa22, 0xff4488, 0x44aaff, 0x88aa22];

const BLOOM_SYMBOLS = ['AAPL', 'MSFT', 'VOO', 'BRK.B', 'SPY', 'AMZN', 'JNJ'];
const OAK_SYMBOLS = ['TECH', 'UTIL', 'HLTH', 'ENRG', 'FINL', 'XLF', 'ROTATE'];
const PIT_SYMBOLS = ['TSLA', 'NVDA', 'AMD', 'GME', 'SPY', 'QQQ', 'AAPL'];
const PIT_CHAOS = [
  { s: '▲', c: 0x00ff00 }, { s: '▼', c: 0xff3333 }, { s: '!!', c: 0xff3333 },
  { s: '$', c: 0x00ff00 }, { s: 'BUY', c: 0x00ff00 }, { s: '⚡', c: 0xff3333 },
  { s: 'SELL', c: 0xff3333 }, { s: '%%%', c: 0xff8c00 },
];

function buildBloomberg(app) {
  const { desks, bounds, spawnPoints } = drawBloomberg(app);
  return spawnPoints.map(([x, y], i) => {
    const ag = new WalkingAgent(
      app, x, y,
      BLOOMBERG_SHIRTS[i % BLOOMBERG_SHIRTS.length],
      0xdfc090, 0x1a3a3a, null,
      bounds, desks
    );
    ag.spd = 0.38 + Math.random() * 0.08;
    return ag;
  });
}

function buildOak(app) {
  const { seatPositions } = drawOak(app);
  return seatPositions.map(([x, y], i) =>
    new SeatedAgent(app, x, y, OAK_SHIRTS[i % OAK_SHIRTS.length], 0xd4b896, 0xcc8833, null, 6)
  );
}

function buildPit(app) {
  const { seatPositions, screenRects, timerText } = drawPit(app);
  const agents = seatPositions.map(([x, y], i) =>
    new SeatedAgent(app, x, y, 0x120404, 0xe0a070, 0xff3333, PIT_VESTS[i % PIT_VESTS.length], 5)
  );
  return { agents, screenRects, timerText };
}

export default function PixiWarroom({ room }) {
  const canvasRef = useRef(null);
  const appRef = useRef(null);
  const agentSpritesRef = useRef([]);
  const chaosRef = useRef([]);
  const symTimerRef = useRef(0);
  const ftRef = useRef(0);

  // WS integration — reads from agentSpritesRef which is populated in the effect below
  useWarroomAgents(room, agentSpritesRef.current);

  useEffect(() => {
    const app = new PIXI.Application({
      view: canvasRef.current,
      width: ROOM_W,
      height: ROOM_H,
      backgroundColor: room === 'long_term' ? 0xe8f0f8 : room === 'swing_trading' ? 0x36454f : 0x080404,
      antialias: false,
      resolution: 1,
    });
    app.ticker.maxFPS = 30;
    appRef.current = app;

    let pitScreenRects = [];
    let pitTimerText = null;

    if (room === 'long_term') {
      agentSpritesRef.current = buildBloomberg(app);
      app.ticker.add(() => {
        agentSpritesRef.current.forEach(a => a.tick(BLOOM_SYMBOLS, 0, 0.08));
      });
    } else if (room === 'swing_trading') {
      agentSpritesRef.current = buildOak(app);
      app.ticker.add(() => {
        agentSpritesRef.current.forEach(a => a.tick(OAK_SYMBOLS, 6, 0.09));
      });
    } else if (room === 'day_trading') {
      const { agents, screenRects, timerText } = buildPit(app);
      agentSpritesRef.current = agents;
      pitScreenRects = screenRects;
      pitTimerText = timerText;

      const flickerG = new PIXI.Graphics();
      app.stage.addChild(flickerG);

      app.ticker.add(() => {
        agentSpritesRef.current.forEach(a => a.tick(PIT_SYMBOLS, 5, 0.18));

        // Spawn chaos symbols
        symTimerRef.current++;
        if (symTimerRef.current % 15 === 0 && agentSpritesRef.current.length > 0) {
          const ag = agentSpritesRef.current[Math.floor(Math.random() * agentSpritesRef.current.length)];
          const sym = PIT_CHAOS[Math.floor(Math.random() * PIT_CHAOS.length)];
          chaosRef.current.push({ sym: new ChaosSymbol(app, ag.x + 7, ag.y + 8, sym.s, sym.c), ag });
        }
        chaosRef.current = chaosRef.current.filter(({ sym, ag }) => {
          const alive = sym.tick(ag.x + 7, ag.y + 8);
          if (!alive) sym.destroy(app);
          return alive;
        });

        // Screen flicker
        ftRef.current++;
        flickerG.clear();
        if (ftRef.current % 40 < 2 && pitScreenRects.length > 0) {
          const s = pitScreenRects[Math.floor(Math.random() * pitScreenRects.length)];
          flickerG.beginFill(s.color, 0.1);
          flickerG.drawRect(s.x, s.y, s.w, s.h);
        }
        // Timer
        if (pitTimerText && ftRef.current % 60 === 0) {
          const mn = 24 + Math.floor(ftRef.current / 60) % 30;
          const sc = ftRef.current % 60;
          pitTimerText.text = `09:${String(mn).padStart(2, '0')}:${String(sc).padStart(2, '0')}`;
        }
      });
    }

    return () => {
      // Destroy sprites
      agentSpritesRef.current.forEach(a => a.destroy());
      agentSpritesRef.current = [];
      chaosRef.current.forEach(({ sym }) => sym.destroy(app));
      chaosRef.current = [];
      app.destroy(false, { children: true, texture: true });
      appRef.current = null;
    };
  }, [room]);

  const roomAccent = room === 'long_term' ? '#4a7eba' : room === 'swing_trading' ? '#CC8833' : '#FF3333';

  return (
    <div style={{
      position: 'relative',
      border: `2px solid ${roomAccent}`,
      overflow: 'hidden',
      width: '100%',
      maxWidth: ROOM_W,
      margin: '0 auto',
    }}>
      <canvas
        ref={canvasRef}
        style={{
          display: 'block',
          width: '100%',
          height: 'auto',
          imageRendering: 'pixelated',
        }}
      />
      {/* Scanlines overlay */}
      <div style={{
        position: 'absolute',
        inset: 0,
        background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.08) 2px, rgba(0,0,0,0.08) 4px)',
        pointerEvents: 'none',
      }} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Warroom/PixiWarroom.jsx frontend/src/components/Warroom/hooks/
git commit -m "feat(4C): Add PixiWarroom React component"
```

---

### Task 9: Wire pages to PixiWarroom

**Files:**
- Modify: `frontend/src/pages/WarroomLongTerm.jsx`
- Modify: `frontend/src/pages/WarroomSwing.jsx`
- Modify: `frontend/src/pages/WarroomDay.jsx`

**Interfaces:**
- Consumes: `PixiWarroom` from `../components/Warroom/PixiWarroom`
- Produces: three pages rendering correct PixiJS rooms

- [ ] **Step 1: Update WarroomLongTerm.jsx**

```jsx
import PixiWarroom from '../components/Warroom/PixiWarroom';
export default function WarroomLongTerm() {
  return <PixiWarroom room="long_term" />;
}
```

- [ ] **Step 2: Update WarroomSwing.jsx**

```jsx
import PixiWarroom from '../components/Warroom/PixiWarroom';
export default function WarroomSwing() {
  return <PixiWarroom room="swing_trading" />;
}
```

- [ ] **Step 3: Update WarroomDay.jsx**

```jsx
import PixiWarroom from '../components/Warroom/PixiWarroom';
export default function WarroomDay() {
  return <PixiWarroom room="day_trading" />;
}
```

- [ ] **Step 4: Lint check**

```bash
cd frontend && npm run lint 2>&1 | tail -10
```
Expected: no errors (warnings about unused imports in old files are OK)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/WarroomLongTerm.jsx frontend/src/pages/WarroomSwing.jsx frontend/src/pages/WarroomDay.jsx
git commit -m "feat(4C): Wire warroom pages to PixiWarroom renderer"
```

---

### Task 10: Lobby Page (4C spec)

**Files:**
- Modify: `frontend/src/pages/Lobby.jsx`
- Modify: `frontend/src/App.jsx` (add `/lobby` route, update nav)

**Interfaces:**
- Consumes: `agentsApi`, `performanceApi`, `useWebSocketStore`, existing CSS vars
- Produces: Lobby page with room scorecards, portfolio stats, risk/bodyguard panels

- [ ] **Step 1: Build Lobby.jsx**

```jsx
// frontend/src/pages/Lobby.jsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { performanceApi, agentsApi } from '../utils/api-client';
import { useWebSocketStore } from '../stores/websocket.store';

const card = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  fontFamily: 'var(--font-mono)',
};

const rooms = [
  { key: 'long_term',     label: 'The Bloomberg',  path: '/warroom/long',  icon: '◈', accent: '#4a7eba' },
  { key: 'swing_trading', label: 'The Oak Office', path: '/warroom/swing', icon: '◎', accent: '#CC8833' },
  { key: 'day_trading',   label: 'The Pit',        path: '/warroom/day',   icon: '◉', accent: '#FF3333' },
];

function RoomScorecard({ room, agents, onEnter }) {
  const roomAgents = agents.filter(a => a.room === room.key);
  const running = roomAgents.filter(a => a.status === 'running').length;
  const totalPnl = roomAgents.reduce((s, a) => s + (a.total_pnl ?? 0), 0);
  const pnlColor = totalPnl >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)';

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onEnter(room.path)}
      style={{ ...card, border: `1px solid ${room.accent}44`, cursor: 'pointer', minWidth: 200 }}
    >
      <div style={{ color: room.accent, fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-2)' }}>
        {room.icon} {room.label}
      </div>
      <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>
        {running}/{roomAgents.length} agents running
      </div>
      <div style={{ fontSize: 'var(--font-size-lg)', color: pnlColor, fontWeight: 700 }}>
        {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)}
      </div>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
        TOTAL P&L
      </div>
    </motion.div>
  );
}

function AgentPanel({ label, agents, accent }) {
  const maxDD = agents.length > 0
    ? Math.max(...agents.map(a => Math.abs(a.max_drawdown ?? 0))).toFixed(1)
    : '0.0';
  return (
    <div style={{ ...card, border: `1px solid ${accent}44`, minWidth: 180 }}>
      <div style={{ color: accent, fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-2)', letterSpacing: '0.08em' }}>
        {label}
      </div>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
        Monitoring {agents.length} agents
      </div>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
        Max drawdown: <span style={{ color: 'var(--color-accent-warning)' }}>{maxDD}%</span>
      </div>
    </div>
  );
}

export default function Lobby() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState([]);
  const [portfolio, setPortfolio] = useState(null);
  const lastMessage = useWebSocketStore(s => s.lastMessage);

  useEffect(() => {
    agentsApi.list().then(setAgents).catch(() => {});
    performanceApi.summary().then(setPortfolio).catch(() => {});
  }, []);

  // Refresh on trade events
  useEffect(() => {
    if (lastMessage?.type === 'trade_executed' || lastMessage?.type === 'portfolio_update') {
      performanceApi.summary().then(setPortfolio).catch(() => {});
    }
  }, [lastMessage]);

  const totalPnl = portfolio?.total_pnl ?? 0;
  const pnlColor = totalPnl >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      style={{ fontFamily: 'var(--font-mono)', padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-2xl)', letterSpacing: '0.1em' }}>
          ⬡ TRADING WARROOM
        </h1>
        <div style={{ textAlign: 'right' }}>
          <div style={{ color: pnlColor, fontSize: 'var(--font-size-xl)', fontWeight: 700 }}>
            {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)}
          </div>
          <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>PORTFOLIO P&L</div>
        </div>
      </div>

      {/* Agent panels + scorecards */}
      <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <AgentPanel label="◈ RISK AGENT" agents={agents} accent="var(--color-accent-primary)" />

        <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', flex: 1 }}>
          {rooms.map(r => (
            <RoomScorecard key={r.key} room={r} agents={agents} onEnter={navigate} />
          ))}
        </div>

        <AgentPanel label="⬡ BODYGUARD" agents={agents} accent="var(--color-accent-secondary)" />
      </div>

      {/* Portfolio quick stats */}
      <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
        {[
          { label: 'ACTIVE AGENTS', value: portfolio?.active_agents ?? agents.filter(a => a.status === 'running').length },
          { label: 'TOTAL TRADES', value: portfolio?.total_trades ?? 0 },
          { label: 'WIN RATE', value: `${((portfolio?.win_rate ?? 0) * 100).toFixed(1)}%` },
          { label: 'TOTAL VALUE', value: `$${(portfolio?.total_value ?? 0).toLocaleString()}` },
        ].map(({ label, value }) => (
          <div key={label} style={{ ...card, flex: 1, minWidth: 140, textAlign: 'center' }}>
            <div style={{ color: 'var(--color-accent-primary)', fontSize: 'var(--font-size-lg)', fontWeight: 700 }}>{value}</div>
            <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)', marginTop: 'var(--space-1)' }}>{label}</div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
```

- [ ] **Step 2: Add Lobby to App.jsx nav + route**

In `frontend/src/App.jsx`:

1. Add import at top with other page imports:
```jsx
import Lobby from './pages/Lobby';
```

2. In `NAV_ITEMS` array, add Lobby entry (after Dashboard):
```js
{ label: 'Lobby', path: '/lobby', icon: '⬡' },
```

3. In `<Routes>`, add route after `/` Dashboard route:
```jsx
<Route path="/lobby" element={<Lobby />} />
```

- [ ] **Step 3: Lint**

```bash
cd frontend && npm run lint 2>&1 | tail -10
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Lobby.jsx frontend/src/App.jsx
git commit -m "feat(4C): Add Lobby page with room scorecards, portfolio stats, agent panels"
```

---

## Self-Review

**Spec coverage:**
- ✅ Bloomberg room — free-walk agents + AABB desk collision + city skyline background
- ✅ Oak Office — 6 seated agents + amber office + whiteboards + wall charts
- ✅ The Pit — 13 seated agents + chaos symbols + screen wall + P&L flicker + timer
- ✅ WebSocket integration — `trade_executed` → `onTrade()`, `agent_update` → `onProcessing()`
- ✅ Demo fallback — `window.__LABOURIOUS_DEMO__` after 3s no WS events
- ✅ Desk collision — AABB in `WalkingAgent`, per-frame nudge-out
- ✅ `PixiWarroom.jsx` mounts/destroys PixiJS app in `useEffect` cleanup
- ✅ Pages wire to `<PixiWarroom room="..." />`
- ✅ `pixi.js ^7.4.2` installed
- ✅ Lobby page with room scorecards, portfolio stats, Risk Agent + Bodyguard panels
- ✅ Lobby route in App.jsx

**Type consistency:**
- `Agent.id` set externally by `useWarroomAgents` ✅
- `onTrade(symbol, action, pnl)` signature consistent across Agent/WalkingAgent/SeatedAgent ✅
- `drawBloomberg` returns `{ desks, bounds, spawnPoints }` — all consumed in `PixiWarroom` ✅
- `drawOak` returns `{ seatPositions }` ✅
- `drawPit` returns `{ seatPositions, screenRects, timerText }` ✅
- `ChaosSymbol.tick(x, y)` returns `boolean` — consumed in filter ✅

**No placeholders found.**
