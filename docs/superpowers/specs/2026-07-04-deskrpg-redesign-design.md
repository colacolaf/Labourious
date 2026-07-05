# DeskRPG Frontend Redesign — Frozen Visual Spec

> Phase 11 frozen design. Reference: [DeskRPG](https://github.com/dandacompany/deskrpg)

## Constants (all rooms)

| Constant | Value |
|----------|-------|
| `MAP_COLS` | 40 |
| `MAP_ROWS` | 30 |
| `TILE_SIZE` | 32 |
| Canvas size | 1280 × 960 |
| Camera zoom | 2× |
| Character display | 48 × 48 px |
| Max agents | 20 per room |
| FPS target | 60 |

## Tile indices (`T`)

| ID | Name | Investment palette | Sector palette | Cubicle palette |
|----|------|-------------------|----------------|-----------------|
| 0 | EMPTY | transparent | transparent | transparent |
| 1 | FLOOR | `#8b8378` wood carpet | `#f5f5f5` white floor | `#6b7280` gray carpet |
| 2 | WALL | `#4a4a5e` warm gray | `#ffffff` white wall | `#9ca3af` cool gray |
| 7 | DOOR | lighter gap | white frame | blue frame `#3b82f6` |
| 12 | CARPET | `#7a7368` meeting area | `#eeeeee` light gray | `#5b6370` |

Object tiles (3–15) render as `MapObject` graphics, not tile layer paint.

## MapData JSON Schema

```json
{
  "name": "investment-room",
  "roomKey": "long_term",
  "theme": "investment",
  "layers": {
    "floor": "number[30][40]",
    "walls": "number[30][40]"
  },
  "objects": [
    { "id": "obj-1", "type": "desk", "col": 12, "row": 18, "direction": "down" }
  ],
  "agentSlots": [
    { "id": "slot-0", "col": 12, "row": 18, "facing": "down" }
  ],
  "metadata": {
    "spawnCol": 20,
    "spawnRow": 25,
    "cameraCenter": { "col": 20, "row": 15 }
  }
}
```

### Object types (V1)

`desk`, `chair`, `computer`, `plant`, `bookshelf`, `meeting_table`, `coffee`, `water_cooler`, `whiteboard`, `reception_desk`, `cubicle_wall`, `paper_stack`, `sector_poster`, `monitor_wall`

## LPC Asset Paths

| Asset | Path |
|-------|------|
| Registry | `frontend/public/assets/lpc-registry.json` |
| Spritesheets | `frontend/public/assets/spritesheets/{category}/walk/{variant}.png` |
| Tileset (runtime) | BootScene generates `office-tiles` texture (512×32); static fallback `frontend/public/assets/tilesets/office.png` |
| Fallback char | `fallback-char` 64×64 placeholder |

### CharacterAppearance

```typescript
interface CharacterAppearance {
  bodyType: "male" | "female";
  layers: Record<string, { itemKey: string; variant: string } | null>;
}
```

Walk sheet output: 576×256 (9 cols × 4 rows × 64px frames).

---

## Room 1: Investment Office (`long_term`)

**Map file:** `frontend/public/maps/investment-room.json`  
**Theme:** DeskRPG default office — warm wood floor, reception, meeting table, plants.

### ASCII floor plan (40×30, `#` wall, `.` floor, letters = objects)

```
########################################
#R.....................................#  R=reception_desk (row 2, col 2)
#......................................#
#..PP..............................PP..#  P=plant
#......................................#
#....DDc..........................DDc.#  D=desk, c=chair, C=computer
#....C..............................C...#
#......................................#
#...........MMMM.......................#  M=meeting_table (2×2)
#...........MMMM.......................#
#......................................#
#....DDc..........DDc..........DDc.....#
#....C............C............C.......#
#......................................#
#....DDc..........DDc..........DDc.....#
#....C............C............C.......#
#......................................#
#....DDc..........DDc..........DDc.....#
#....C............C............C.......#
#......................................#
#..CO.............................WC...#  CO=coffee, WC=water_cooler
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
########################################
```

### Object inventory

| Type | Count | Notes |
|------|-------|-------|
| reception_desk | 1 | Entrance, col 2–3, row 2 |
| meeting_table | 2 | Center-left, 2×2 each |
| desk + chair + computer | 8 | Three rows of workstations |
| plant | 4 | Corners near top |
| coffee | 1 | Left bottom area |
| water_cooler | 1 | Right bottom area |

### Agent slots: 7

Positions at desk chairs facing computers. Idle wander within floor bounds.

### Screenshot target

Match DeskRPG README office screenshot: warm palette, wood desks, reception at top-left, meeting tables center.

---

## Room 2: Sector Trading Office (`swing_trading`)

**Map file:** `frontend/public/maps/sector-room.json`  
**Theme:** White analyst floor — whiteboards, sector posters, paper stacks.

### Palette overrides

- Floor: `#f5f5f5` (tile index 1 tinted)
- Walls: `#ffffff`
- Accent: `#d97706` amber (whiteboard chart lines)
- Whiteboards: 3 along top wall — labels XLF, XLE, XLK

### ASCII floor plan

```
########################################
#WWW..............................WWW..#  W=whiteboard (top wall)
#......................................#
#..PP..............................PP..#  P=sector_poster
#......................................#
#....DDc....DDc....DDc....DDc....DDc...#  2 cols × 3 rows desks
#....C......C......C......C......C.....#
#....DDc....DDc....DDc....DDc....DDc...#
#....C......C......C......C......C.....#
#....DDc....DDc....DDc....DDc....DDc...#
#....C......C......C......C......C.....#
#......................................#
#..ps....ps........ps....ps........ps..#  ps=paper_stack
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
########################################
```

### Object inventory

| Type | Count |
|------|-------|
| whiteboard | 3 |
| sector_poster | 2 |
| desk + chair + computer | 6 (2×3 grid) |
| paper_stack | 5 |
| plant | 0 |

### Agent slots: 6

Seated at desks; micro-wander ±8px.

### Sector decor (Phaser Graphics)

- Whiteboard: amber line charts, ticker labels
- Paper piles: stacked gray rects + crumpled floor decals

---

## Room 3: Day Trading Floor (`day_trading`)

**Map file:** `frontend/public/maps/day-trading-room.json`  
**Theme:** Cubicle maze — `cubicle_wall` partitions, monitor wall strip.

### Palette

- Carpet: `#6b7280`
- Cubicle walls: `#888899` at 50% visual height
- Accent: `#3b82f6` blue (monitors, doors)
- Energy: higher contrast than investment, **not** old red/black Pit

### ASCII floor plan

```
########################################
#MMMMM.................................#  M=monitor_wall (top strip)
#......................................#
#..Cu..Cu..Cu..Cu..Cu..Cu..Cu..Cu.....#  Cu=cubicle pod row 1
#..DDc..DDc..DDc..DDc..DDc..DDc.......#
#..Cu..Cu..Cu..Cu..Cu..Cu..Cu..Cu.....#  row 2
#..DDc..DDc..DDc..DDc..DDc..DDc.......#
#..Cu..Cu..Cu..Cu..Cu..Cu..Cu..Cu.....#  row 3
#..DDc..DDc..DDc..DDc..DDc..DDc.......#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
#......................................#
########################################
```

### Object inventory

| Type | Count |
|------|-------|
| cubicle_wall | ~24 (3 rows × 8 pods) |
| desk + chair + computer | 12–13 |
| monitor_wall | 5 | Top strip, flicker every 40 frames |

### Agent slots: 13

### Screenshot target

Dense cubicle farm, blue monitor glow, distinct from investment + sector.

---

## Head Bubble Events (from LABOURIOUS_FRONTEND.md)

**Style:** Modern — rounded rect `rgba(15,23,42,0.92)`, 1px border, `11px JetBrains Mono`. **No** CRT, scanlines, Press Start 2P.

| Event | Content | Color | Duration |
|-------|---------|-------|----------|
| `trade_executed` win | `✅ +$1,240` or `BUY AAPL` | `#22c55e` | 2.5s + 0.5s fade |
| `trade_executed` loss | `❌ -$340` or `SELL TSLA` | `#ef4444` | same |
| `trade_approval_needed` | `⚠️ Approve?` + countdown | `#f59e0b` | until resolved |
| `agent_paused` | `🔒 Losing streak` | `#fb923c` | persistent |
| `agent_update` processing | spinning arc | white | 90 frames |
| confidence | `72%` | body tint per threshold | 1.5s |

## Preserved React Shell

- `AgentInspector.jsx` — click sprite → `useAgentsStore.selectAgent` + `useUIStore.openInspector`
- `ApprovalDialog.jsx` — syncs with approval bubble countdown
- `useWarroomAgents` — WS events → `TradingAgent` methods
- `window.__LABOURIOUS_DEMO__` — after 3s no WS events

## Room key mapping

| Backend `room` | Page | Map JSON | Theme |
|----------------|------|----------|-------|
| `long_term` | WarroomLongTerm | investment-room | investment |
| `swing_trading` | WarroomSwing | sector-room | sector |
| `day_trading` | WarroomDay | day-trading-room | cubicle |
