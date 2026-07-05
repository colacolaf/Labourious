# Phase 11 — DeskRPG Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Labourious’s retro PixiJS warrooms with a [DeskRPG](https://github.com/dandacompany/deskrpg)-style pixel-art office experience: Phaser 3 tilemaps, LPC character sprites, three distinct trading rooms, live backend-driven head animations, and user-editable rooms/characters.

**Architecture:** Migrate the warroom renderer from procedural PixiJS (`PixiWarroom.jsx`) to a Phaser 3 + React bridge (DeskRPG pattern: `EventBus`, `WarroomPhaserGame.jsx`, `WarroomScene.ts`). Keep existing Zustand stores, WebSocket feed, and React inspector/approval UI. Room layouts ship as JSON `MapData` (floor/walls/objects); agents render as composited LPC sprites with a `HeadBubble` system that preserves `docs/LABOURIOUS_FRONTEND.md` notification semantics without retro CRT styling.

**Tech Stack:** Phaser ^3.90.0, React 18, Zustand, Framer Motion (React overlays only), existing `useWebSocketStore` + `agentsApi`, LPC assets from DeskRPG (`public/assets/lpc-*`), optional new backend endpoints for appearance/map persistence.

## Global Constraints

- **Reference repo:** `https://github.com/dandacompany/deskrpg` — port patterns, not fork the whole Next.js app. Adapt `EventBus`, `sprite-compositor`, `lpc-registry`, `object-types`, `GameScene` tile constants.
- **Room mapping (Labourious → visual theme):**
  - `long_term` → **Investment Room** — match DeskRPG default office almost exactly (warm wood floor, desks, plants, reception, meeting table).
  - `swing_trading` → **Sector Trading Room** — same LPC/tile engine, **white** palette: white walls/floor, whiteboards, sector posters, paper stacks, desks + computers.
  - `day_trading` → **Day Trading Room** — DeskRPG cubicle layout (`cubicle_wall`, dense desks, screen-wall feel).
- **Head animations:** Follow `docs/LABOURIOUS_FRONTEND.md` § AgentSprite / TradeNotification event types (trade ✅/❌, approval ⚠️, paused 🔒, confidence %, processing spinner). **Do not** use retro scanlines, Press Start 2P, CRT glow, or beveled buttons in warroom canvas or bubbles.
- **Backend binding:** All agent sprites must map 1:1 to `GET /api/agents?room=` records and react to existing WS events via an extended `useWarroomAgents` hook.
- **Preserve:** `AgentInspector.jsx`, `ApprovalDialog.jsx`, Control Room, Analytics, auth, wizard — restyle shells only in Task 9.
- **CSS vars:** Warroom React chrome uses `var(--color-*)`, `var(--font-*)`, `var(--space-*)`. Phaser canvas uses fixed pixel palette per room JSON; no hardcoded retro terminal greens in UI chrome.
- **Performance:** 40×30 tile map, 32px tiles, camera zoom 2×, 60 FPS target, max 20 agents per room.
- **Demo fallback:** Keep `window.__LABOURIOUS_DEMO__` after 3s with no WS events.
- **Tests:** `cd frontend && npm test -- --watchAll=false` for new stores/utilities; manual room smoke test per task.
- **Deprecate (do not delete until Task 9):** `PixiWarroom.jsx`, `rooms/bloomberg.js`, `rooms/oak.js`, `rooms/pit.js`, procedural `sprites/Agent.js` hierarchy.

---

## Design Reference (DeskRPG → Labourious)

| DeskRPG concept | Labourious use |
|-----------------|----------------|
| `MAP_COLS=40`, `MAP_ROWS=30`, `TILE_SIZE=32` | All three rooms |
| `T` tile constants + `OBJECT_TYPES` | Furniture placement |
| LPC `CharacterAppearance` + `compositeCharacter()` | Agent + user avatar sprites |
| `GameScene` y-sort depth, A* optional | Agent desk seating / idle wander |
| `AppearanceEditor.tsx` | Task 10 character editor |
| `map-editor/*` | Task 10 room editor |
| Head labels on sprites | Replace with `HeadBubble` trading events |

### Head bubble event map (from LABOURIOUS_FRONTEND.md)

| Event | Bubble content | Color | Duration |
|-------|----------------|-------|----------|
| `trade_executed` (win) | `✅ +$1,240` or `BUY AAPL` | green `#22c55e` | 2.5s hold + 0.5s fade |
| `trade_executed` (loss) | `❌ -$340` or `SELL TSLA` | red `#ef4444` | same |
| `trade_approval_needed` | `⚠️ Approve?` + countdown | amber `#f59e0b` | until resolved |
| `agent_paused` | `🔒 Losing streak` | orange `#fb923c` | persistent until unpaused |
| `agent_update` (processing) | spinning arc above head | white | 90 frames |
| confidence broadcast | `72%` brief flash | tint body per existing thresholds | 1.5s |

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `docs/superpowers/specs/2026-07-04-deskrpg-redesign-design.md` | Create | Frozen visual spec + room JSON schemas |
| `frontend/package.json` | Modify | Add `phaser@^3.90.0`; keep `pixi.js` until Task 9 removal |
| `frontend/public/assets/lpc/` | Create | Copy LPC registry + spritesheets from DeskRPG |
| `frontend/public/assets/tilesets/office.png` | Create | DeskRPG-compatible 32px tileset |
| `frontend/public/maps/investment-room.json` | Create | Default long_term layout (DeskRPG clone) |
| `frontend/public/maps/sector-room.json` | Create | White sector room layout |
| `frontend/public/maps/day-trading-room.json` | Create | Cubicle layout |
| `frontend/src/game/EventBus.ts` | Create | React ↔ Phaser pub/sub |
| `frontend/src/game/main.ts` | Create | `createGame(containerId)` factory |
| `frontend/src/game/scenes/BootScene.ts` | Create | Load tileset + default textures |
| `frontend/src/game/scenes/WarroomScene.ts` | Create | Render map, spawn agents, head bubbles |
| `frontend/src/lib/lpc-registry.ts` | Create | Port from DeskRPG |
| `frontend/src/lib/sprite-compositor.ts` | Create | Port from DeskRPG |
| `frontend/src/lib/object-types.ts` | Create | Port from DeskRPG |
| `frontend/src/lib/map-loader.ts` | Create | Load JSON → Phaser layers |
| `frontend/src/components/Warroom/WarroomPhaserGame.jsx` | Create | React wrapper (replaces PixiWarroom) |
| `frontend/src/components/Warroom/sprites/TradingAgent.ts` | Create | LPC sprite + HeadBubble + WS callbacks |
| `frontend/src/components/Warroom/sprites/HeadBubble.ts` | Create | Floating notification renderer |
| `frontend/src/components/Warroom/hooks/useWarroomAgents.js` | Modify | Dispatch to Phaser TradingAgent instances |
| `frontend/src/pages/WarroomLongTerm.jsx` | Modify | `<WarroomPhaserGame room="long_term" map="investment-room" />` |
| `frontend/src/pages/WarroomSwing.jsx` | Modify | `<WarroomPhaserGame room="swing_trading" map="sector-room" />` |
| `frontend/src/pages/WarroomDay.jsx` | Modify | `<WarroomPhaserGame room="day_trading" map="day-trading-room" />` |
| `frontend/src/styles/deskrpg-theme.css` | Create | New palette (Task 9) |
| `frontend/src/components/Editor/RoomEditor/` | Create | Task 10 — map editor port |
| `frontend/src/components/Editor/CharacterEditor/` | Create | Task 10 — appearance editor port |
| `backend/api/room_layouts.py` | Create | Task 10 — CRUD room JSON |
| `backend/api/agent_appearance.py` | Create | Task 10 — CRUD LPC appearance JSON |
| `backend/database/models.py` | Modify | Task 10 — `room_layouts`, `agent_appearance` columns/tables |

---

### Task 1: Design spec + Phaser/LPC foundation

**Files:**
- Create: `docs/superpowers/specs/2026-07-04-deskrpg-redesign-design.md`
- Modify: `frontend/package.json`
- Create: `frontend/public/assets/lpc/` (copy from DeskRPG)
- Create: `frontend/public/assets/tilesets/office.png`

**Interfaces:**
- Produces: frozen room palettes, `MapData` JSON schema, LPC asset paths documented
- Produces: `import Phaser from 'phaser'` resolves in frontend build

- [x] **Step 1: Write design spec** — document the three room layouts with ASCII floor plans, tile/object lists, spawn points per room, and screenshot targets referencing DeskRPG README images.

- [x] **Step 2: Add Phaser dependency**

```json
"phaser": "^3.90.0"
```

Run: `cd frontend && npm install`

- [x] **Step 3: Copy DeskRPG LPC assets**

```bash
# From a temp clone of deskrpg
cp -R deskrpg/public/assets/lpc-registry.json frontend/public/assets/
cp -R deskrpg/public/assets/lpc frontend/public/assets/
cp deskrpg/public/assets/tilesets/*.png frontend/public/assets/tilesets/
```

- [x] **Step 4: Verify Phaser import**

```bash
cd frontend && node -e "require('phaser'); console.log('ok')"
```

Expected: `ok`

- [x] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-07-04-deskrpg-redesign-design.md frontend/package.json frontend/package-lock.json frontend/public/assets/
git commit -m "feat(11.1): DeskRPG design spec + Phaser/LPC asset foundation"
```

---

### Task 2: Phaser/React bridge + BootScene

**Files:**
- Create: `frontend/src/game/EventBus.ts`
- Create: `frontend/src/game/main.ts`
- Create: `frontend/src/game/scenes/BootScene.ts`
- Create: `frontend/src/components/Warroom/WarroomPhaserGame.jsx`

**Interfaces:**
- Consumes: Phaser 3, design spec tileset path
- Produces:
  - `EventBus.emit(event, payload)` / `EventBus.on(event, handler)`
  - `createGame(containerId: string): Phaser.Game`
  - `<WarroomPhaserGame room="" map="" onAgentClick={(agentId) => void} />` — mounts canvas, emits `scene-ready`

- [x] **Step 1: Port EventBus** (from `deskrpg/src/game/EventBus.ts`) — events: `scene-ready`, `spritesheet-ready`, `agent-clicked`, `map-loaded`.

- [x] **Step 2: Create BootScene** — preload `office` tileset, `fallback-char` 1×1 pixel, LPC body placeholder.

- [x] **Step 3: Create main.ts**

```typescript
import Phaser from 'phaser';
import { BootScene } from './scenes/BootScene';

export function createGame(parent: string) {
  return new Phaser.Game({
    type: Phaser.AUTO,
    parent,
    width: 1280,
    height: 960,
    pixelArt: true,
    backgroundColor: '#2d2d2d',
    scene: [BootScene],
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  });
}
```

- [x] **Step 4: Create WarroomPhaserGame.jsx** — mirror DeskRPG `PhaserGame.tsx` lifecycle: dynamic import, StrictMode guard, destroy on unmount, `useLayoutEffect` for container sizing.

- [x] **Step 5: Smoke test** — render `<WarroomPhaserGame room="long_term" map="investment-room" />` on a dev-only route; expect gray canvas + BootScene loaded log via `EventBus`.

- [x] **Step 6: Commit**

```bash
git add frontend/src/game/ frontend/src/components/Warroom/WarroomPhaserGame.jsx
git commit -m "feat(11.2): Phaser/React bridge + BootScene"
```

---

### Task 3: LPC compositor + lib ports

**Files:**
- Create: `frontend/src/lib/lpc-registry.ts`
- Create: `frontend/src/lib/sprite-compositor.ts`
- Create: `frontend/src/lib/object-types.ts`
- Create: `frontend/src/lib/map-loader.ts`

**Interfaces:**
- Produces:
  - `compositeCharacter(canvas, appearance): Promise<void>`
  - `CharacterAppearance`, `normalizeAppearance()`, `OBJECT_TYPES`, `MapData`
  - `loadMapIntoScene(scene, mapData, tilesetKey): { spawnPoints: {x,y}[], seatMap: Record<agentSlot,{x,y}> }`

- [x] **Step 1: Port lpc-registry.ts** — point imports at `frontend/public/assets/lpc-registry.json`.

- [x] **Step 2: Port sprite-compositor.ts** — verify one test appearance composites to 576×256 walk sheet.

- [x] **Step 3: Port object-types.ts** — include `whiteboard`, `cubicle_wall`, `computer`, `desk`, `chair`, `plant`.

- [x] **Step 4: Implement map-loader.ts** — render floor layer, wall layer, place objects with y-sort; return agent anchor positions from map metadata block:

```json
"agentSlots": [
  { "id": "slot-0", "col": 12, "row": 18, "facing": "down" }
]
```

- [x] **Step 5: Unit test map-loader**

```javascript
// frontend/src/lib/__tests__/map-loader.test.js
import { computeOccupiedTiles } from '../object-types';
test('desk occupies tile', () => {
  const occupied = computeOccupiedTiles([{ id: '1', type: 'desk', col: 5, row: 5 }]);
  expect(occupied.has('5,5')).toBe(true);
});
```

- [x] **Step 6: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat(11.3): Port LPC compositor, object types, map loader"
```

---

### Task 4: Investment Room (long_term) — DeskRPG clone

**Files:**
- Create: `frontend/public/maps/investment-room.json`
- Create: `frontend/src/game/scenes/WarroomScene.ts`
- Modify: `frontend/src/pages/WarroomLongTerm.jsx`

**Interfaces:**
- Consumes: `loadMapIntoScene`, DeskRPG default office layout (extract from deskrpg `GameScene` default map or bundled channel map)
- Produces: Investment room visually matches DeskRPG office: wood floor, reception desk, meeting table, plants, 6–8 desk stations, warm lighting

**Room requirements (user rule #1):**
- Almost exactly DeskRPG default office — same tileset, same object types, same camera zoom (2×), same character scale (48×48 display).
- Agents walk between desks or sit at assigned slots (A* optional; idle wander within floor bounds acceptable for v1).

- [x] **Step 1: Author `investment-room.json`** — 40×30 grid, floor=wood, walls=perimeter, objects: reception_desk @ entrance, 2× meeting_table, 8× desk+chair+computer pairs, 4× plant, 1× coffee, 1× water_cooler. Include 7 `agentSlots`.

- [x] **Step 2: Implement WarroomScene.ts** — load map by key prop; camera `setBounds`; `MAIN_CAMERA_ZOOM = 2`; depth sort by y.

- [x] **Step 3: Wire WarroomLongTerm.jsx**

```jsx
import WarroomPhaserGame from '../components/Warroom/WarroomPhaserGame';
export default function WarroomLongTerm() {
  return <WarroomPhaserGame room="long_term" map="investment-room" />;
}
```

- [x] **Step 4: Visual QA** — side-by-side screenshot vs DeskRPG home screenshot; desk count, reception, plants must match.

- [x] **Step 5: Commit**

```bash
git add frontend/public/maps/investment-room.json frontend/src/game/scenes/WarroomScene.ts frontend/src/pages/WarroomLongTerm.jsx
git commit -m "feat(11.4): Investment room — DeskRPG office clone"
```

---

### Task 5: Sector Trading Room (swing_trading) — white office

**Files:**
- Create: `frontend/public/maps/sector-room.json`
- Create: `frontend/src/game/scenes/palettes/sector-palette.ts`
- Modify: `frontend/src/pages/WarroomSwing.jsx`

**Interfaces:**
- Produces: White-room variant using same tile engine — `#f5f5f5` floor, `#ffffff` walls, amber accent `#d97706` for chart lines on whiteboards

**Room requirements (user rule #2):**
- Same DeskRPG style/engine as investment room.
- **White room:** white/light-gray floor tiles, white wall tiles.
- **Whiteboards:** 3× along top wall with sector chart doodles (XLF, XLE, XLK labels).
- **Paper:** scattered `paper_stack` objects (custom 1×1 graphic in scene) + crumpled paper decals on floor layer.
- **Desks + computers:** 6 long desk rows (2 columns × 3), each desk + computer + chair.
- **Posters:** wall-mounted sector rotation poster objects (graphic rectangles with ticker text).
- 6 `agentSlots`, seated micro-wander ±8px.

- [x] **Step 1: Extend WarroomScene** — accept `roomTheme: 'investment' | 'sector' | 'cubicle'` prop via EventBus; sector theme swaps floor/wall tint tables.

- [x] **Step 2: Author `sector-room.json`** with white palette indices + object placements per spec.

- [x] **Step 3: Add sector-only graphics** in `WarroomScene.drawSectorDecor()` — hand-drawn whiteboard lines, paper piles (Phaser Graphics).

- [x] **Step 4: Wire WarroomSwing.jsx** — `map="sector-room" room="swing_trading"`.

- [x] **Step 5: Visual QA** — room reads as bright analyst floor, not dark retro pit.

- [x] **Step 6: Commit**

```bash
git add frontend/public/maps/sector-room.json frontend/src/game/scenes/palettes/ frontend/src/pages/WarroomSwing.jsx
git commit -m "feat(11.5): Sector trading room — white office with whiteboards"
```

---

### Task 6: Day Trading Room (day_trading) — cubicles

**Files:**
- Create: `frontend/public/maps/day-trading-room.json`
- Modify: `frontend/src/pages/WarroomDay.jsx`

**Interfaces:**
- Produces: Cubicle maze using `cubicle_wall` objects, 12–13 agent slots, monitor glow on computers

**Room requirements (user rule #3):**
- DeskRPG cubicle tiles (`T.CUBICLE_WALL = 15`).
- 3 rows of cubicle pods, each with desk + computer + chair.
- Optional top “screen wall” strip (5 monitor objects showing live ticker placeholders — flicker every 40 frames).
- Higher energy than investment room but **not** the old red/black Pit palette.

- [x] **Step 1: Author `day-trading-room.json`** — cubicle grid, 13 agentSlots, screen-wall objects row at top.

- [x] **Step 2: Implement cubicle theme** in WarroomScene — cool gray carpet `#6b7280`, blue accent `#3b82f6`, cubicle walls at 50% height depth sort.

- [x] **Step 3: Wire WarroomDay.jsx**

- [x] **Step 4: Visual QA** — reads as cubicle farm, distinct from investment + sector rooms.

- [x] **Step 5: Commit**

```bash
git add frontend/public/maps/day-trading-room.json frontend/src/pages/WarroomDay.jsx
git commit -m "feat(11.6): Day trading room — cubicle layout"
```

---

### Task 7: TradingAgent sprites + backend connection

**Files:**
- Create: `frontend/src/components/Warroom/sprites/TradingAgent.ts`
- Modify: `frontend/src/components/Warroom/hooks/useWarroomAgents.js`
- Modify: `frontend/src/game/scenes/WarroomScene.ts`

**Interfaces:**
- Consumes: `agentsApi.list({ room })`, `useWebSocketStore.lastMessage`, `compositeCharacter`
- Produces:
  - `class TradingAgent` — `id`, `sprite`, `onTrade()`, `onProcessing()`, `setPaused()`, `setConfidence()`, `showApproval()`, `destroy()`
  - `useWarroomAgents(room, tradingAgents: TradingAgent[])` — maps API agents to slots by index then id

- [x] **Step 1: Implement TradingAgent.ts**

```typescript
export class TradingAgent {
  id: string | null = null;
  sprite: Phaser.GameObjects.Sprite;
  headBubble: HeadBubble;

  constructor(scene: Phaser.Scene, x: number, y: number, textureKey: string) {
    this.sprite = scene.add.sprite(x, y, textureKey);
    this.sprite.setOrigin(0.5, 0.85);
    this.sprite.setDisplaySize(48, 48);
    this.sprite.setInteractive({ useHandCursor: true });
    this.headBubble = new HeadBubble(scene, this.sprite);
  }

  async applyAppearance(appearance: CharacterAppearance) {
    const canvas = document.createElement('canvas');
    await compositeCharacter(canvas, appearance);
    const key = `agent-${this.id ?? Math.random()}`;
    this.sprite.scene.textures.addCanvas(key, canvas);
    this.sprite.setTexture(key);
  }
}
```

- [x] **Step 2: Default appearances** — ship 7/6/13 preset LPC outfits per room in `frontend/src/data/default-agent-appearances.json` until Task 10 customization lands.

- [x] **Step 3: WarroomScene spawn loop** — on `scene-ready`, fetch agents, composite textures, place at `agentSlots[i]`, register click → `EventBus.emit('agent-clicked', { agentId })`.

- [x] **Step 4: Extend useWarroomAgents.js** — replace Pixi `agentSprites` array with `TradingAgent[]`; handle events:

| WS key | Action |
|--------|--------|
| `trade_executed` | `onTrade(symbol, action, pnl)` |
| `agent_update` / `agent_paused` | `onProcessing()`, `setPaused()`, `setConfidence()` |
| `trade_approval_needed` | `showApproval(timeoutSeconds)` |
| `bodyguard_pause_all` | `setPaused(true)` on all |

- [x] **Step 5: Wire agent-clicked** in warroom pages — open existing `AgentInspector` via `useAgentsStore.selectAgent(id)` + `useUIStore.openInspector()`.

- [x] **Step 6: Integration test** — with backend running, start agent trade → bubble appears above correct sprite.

- [x] **Step 7: Commit**

```bash
git add frontend/src/components/Warroom/sprites/ frontend/src/components/Warroom/hooks/ frontend/src/game/scenes/WarroomScene.ts frontend/src/data/default-agent-appearances.json
git commit -m "feat(11.7): TradingAgent LPC sprites + backend WS binding"
```

---

### Task 8: Head bubble animation system

**Files:**
- Create: `frontend/src/components/Warroom/sprites/HeadBubble.ts`
- Modify: `frontend/src/components/Warroom/sprites/TradingAgent.ts`

**Interfaces:**
- Produces: `HeadBubble.show(type, payload)` with queue support (max 2 stacked bubbles)

- [ ] **Step 1: Implement HeadBubble.ts** — Phaser Container above sprite (`y - 52`):

```typescript
type BubbleType = 'trade_win' | 'trade_loss' | 'approval' | 'paused' | 'confidence' | 'processing';

export class HeadBubble {
  show(type: BubbleType, text: string, opts?: { durationMs?: number; persistent?: boolean }) { /* ... */ }
  tick(delta: number) { /* fade, float up 12px, processing arc rotation */ }
}
```

Visual style (NOT retro):
- Rounded rect background `rgba(15,23,42,0.92)` + 1px border
- Font: `11px JetBrains Mono` (load via CSS font family in Phaser text config)
- No scanlines, no Press Start 2P

- [ ] **Step 2: Map LABOURIOUS_FRONTEND.md notifications**

```typescript
onTrade(symbol: string, action: string, pnl: number) {
  const win = pnl >= 0 || action === 'BUY';
  this.headBubble.show(win ? 'trade_win' : 'trade_loss',
    win ? `✅ +$${Math.abs(pnl).toFixed(0)}` : `❌ -$${Math.abs(pnl).toFixed(0)}`,
    { durationMs: 3000 });
  this.flashBody(win ? 0x22c55e : 0xef4444);
}
```

- [ ] **Step 3: Approval bubble** — sync with existing `ApprovalDialog.jsx`: when dialog open, bubble shows `⚠️ 30s` countdown; on approve/reject, clear bubble.

- [ ] **Step 4: Paused state** — persistent `🔒 {reason}` bubble until `setPaused(false)`.

- [ ] **Step 5: Confidence flash** — `show('confidence', '${score}%', { durationMs: 1500 })` + reuse Task 5E tint thresholds on sprite.

- [ ] **Step 6: Demo mode** — when `window.__LABOURIOUS_DEMO__`, random bubbles using room symbol lists (same as old Pixi plan).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Warroom/sprites/HeadBubble.ts
git commit -m "feat(11.8): Head bubble trading notification system"
```

---

### Task 9: App shell + lobby redesign (DeskRPG aesthetic)

**Files:**
- Create: `frontend/src/styles/deskrpg-theme.css`
- Modify: `frontend/src/styles/index.css`
- Modify: `frontend/src/pages/Lobby.jsx`
- Modify: `frontend/src/App.jsx`
- Delete (after pages wired): `frontend/src/components/Warroom/PixiWarroom.jsx`, `frontend/src/components/Warroom/rooms/*.js`, old Pixi sprites

**Interfaces:**
- Produces: warm office UI palette inspired by DeskRPG (gray-800 sidebar `#1f2937`, indigo accent `#6366f1`), remove terminal-green retro theme from warroom-facing pages

- [ ] **Step 1: Create deskrpg-theme.css**

```css
:root {
  --color-bg-primary: #111827;
  --color-bg-secondary: #1f2937;
  --color-bg-card: #374151;
  --color-accent-primary: #6366f1;
  --color-accent-secondary: #818cf8;
  --color-text-primary: #f9fafb;
  --color-pnl-positive: #22c55e;
  --color-pnl-negative: #ef4444;
  --font-sans: 'Inter', system-ui, sans-serif;
  /* keep --font-mono for data tables */
}
```

- [ ] **Step 2: Import theme in index.css** — replace retro vars; keep PnL/status semantic names.

- [ ] **Step 3: Redesign Lobby.jsx** — DeskRPG-style channel cards: map thumbnail preview (static PNG per room), agent count, P&L, “Enter Office” button. Risk Agent + Bodyguard as LPC portrait cards (composite mini canvas).

- [ ] **Step 4: Update App.jsx nav** — rename warroom labels: “Investment Office”, “Sector Office”, “Day Trading Floor”; remove retro icons.

- [ ] **Step 5: Remove Pixi warroom** — uninstall `pixi.js` if no other imports; delete deprecated files.

- [ ] **Step 6: Lint + test**

```bash
cd frontend && npm run lint && npm test -- --watchAll=false
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/styles/ frontend/src/pages/Lobby.jsx frontend/src/App.jsx
git commit -m "feat(11.9): DeskRPG theme shell + lobby redesign; remove Pixi warroom"
```

---

### Task 10: Room editor + character editor

**Files:**
- Create: `frontend/src/components/Editor/RoomEditor/` (port from deskrpg `map-editor/`: `MapEditorLayout`, `MapCanvas`, `TilePalette`, `Toolbar`, `LayerPanel`)
- Create: `frontend/src/components/Editor/CharacterEditor/AppearanceEditor.jsx` (port from deskrpg `AppearanceEditor.tsx`)
- Create: `frontend/src/pages/OfficeEditor.jsx`
- Create: `frontend/src/pages/CharacterCustomizer.jsx`
- Create: `backend/api/room_layouts.py`
- Create: `backend/api/agent_appearance.py`
- Modify: `backend/database/models.py`
- Modify: `backend/main.py` (register routers)
- Modify: `frontend/src/utils/api-client.js`

**Interfaces:**
- Produces:
  - `roomLayoutsApi.get(roomKey)`, `.save(roomKey, mapData)`, `.reset(roomKey)`
  - `agentAppearanceApi.get(agentId)`, `.save(agentId, appearance)`, `.getUserAvatar()`, `.saveUserAvatar(appearance)`
  - `/editor/room/:roomKey` — edit floor/walls/objects, preview in Phaser, save to backend
  - `/editor/character/:agentId?` — LPC layer picker, live preview, save

**User requirements (rule #5 + prior notes):**
- Users can edit room layouts (tile paint + object place/delete/rotate).
- Users can edit agent characters (full LPC categories) and optional user avatar.
- Editor uses same `MapData` JSON schema as runtime maps.
- “Reset to default” restores bundled `public/maps/*.json`.

- [ ] **Step 1: Backend — room_layouts table**

```python
# backend/database/models.py
class RoomLayout(Base):
    __tablename__ = "room_layouts"
    room_key = Column(String, primary_key=True)  # long_term | swing_trading | day_trading
    map_json = Column(JSON, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 2: Backend — agent appearance column**

```python
# Add to Agent model
appearance_json = Column(JSON, nullable=True)  # CharacterAppearance blob
```

- [ ] **Step 3: API routes**

```python
# GET/PUT /api/room-layouts/{room_key}
# GET/PUT /api/agents/{id}/appearance
# GET/PUT /api/user/avatar-appearance
```

- [ ] **Step 4: Port map editor UI** — simplify DeskRPG editor: remove multiplayer/channel features; add room selector dropdown (3 rooms); Save calls `roomLayoutsApi.save`.

- [ ] **Step 5: Port AppearanceEditor** — convert TSX → JSX; wire to `agentAppearanceApi`; live preview via `CharacterPreview` compositing canvas.

- [ ] **Step 6: Runtime map resolution** — `WarroomScene` loads `GET /api/room-layouts/{room}` first, falls back to `public/maps/{map}.json`.

- [ ] **Step 7: Runtime appearance resolution** — `TradingAgent.applyAppearance()` prefers agent's saved appearance, else room default preset.

- [ ] **Step 8: Add routes + nav**

```jsx
<Route path="/editor/room/:roomKey" element={<OfficeEditor />} />
<Route path="/editor/character/:agentId?" element={<CharacterCustomizer />} />
```

Add “Customize Office” button on each warroom page header; “Edit Character” in AgentInspector Settings tab.

- [ ] **Step 9: Tests**

```bash
cd backend && pytest tests/test_room_layouts.py -v
cd frontend && npm test -- --watchAll=false --testPathPattern=AppearanceEditor
```

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/Editor/ backend/api/ backend/database/models.py frontend/src/pages/OfficeEditor.jsx frontend/src/pages/CharacterCustomizer.jsx
git commit -m "feat(11.10): Room editor + LPC character customizer with backend persistence"
```

---

## Migration Checklist (post-Task 10)

- [ ] All three warrooms render in Phaser with distinct art direction
- [ ] WS trade events show head bubbles on correct agent
- [ ] AgentInspector opens on sprite click with live data
- [ ] ApprovalDialog syncs with head bubble countdown
- [ ] Room editor saves and reloads custom layouts
- [ ] Character editor saves per-agent LPC appearance
- [ ] No retro scanline/Press Start 2P in warroom canvas
- [ ] PixiJS fully removed from dependencies
- [ ] `docs/LABOURIOUS_FRONTEND.md` updated with “DeskRPG renderer” section (separate docs task)

---

## Self-Review

**Spec coverage:**
- ✅ Investment room ≈ DeskRPG office (Task 4)
- ✅ Sector room — white, whiteboards, paper, desks, computers (Task 5)
- ✅ Day trading — cubicles in DeskRPG style (Task 6)
- ✅ Agents backend-connected + head animations from frontend.md, non-retro styling (Tasks 7–8)
- ✅ Room + character editing as Task 10
- ✅ Prior plan patterns reused: file map, interfaces, WS hook, demo fallback, commit-per-task

**Placeholder scan:** No TBD sections. All tasks have file paths and interface contracts.

**Type consistency:**
- `TradingAgent` + `HeadBubble` used consistently in Tasks 7–8
- `MapData` / `agentSlots` schema consistent across Tasks 3–6 and Task 10
- Room keys `long_term | swing_trading | day_trading` unchanged (backend compatible)

**Risk notes:**
- LPC asset bundle is large (~MB); lazy-load per room if bundle size exceeds Electron budget.
- Phaser in Electron requires `webSecurity` check for local asset paths — mirror DeskRPG `file://` handling in `electron-main.js` if needed.
- Map editor port is the largest sub-effort; consider shipping read-only room preview in Task 9 and full editor in Task 10 if schedule slips.

---

## Execution Handoff

**Plan saved to `docs/superpowers/plans/2026-07-04-phase11-deskrpg-frontend-redesign.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks
2. **Inline Execution** — execute tasks in this session with checkpoints

Which approach do you want?
