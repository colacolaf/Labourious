# Warroom Rooms Design Spec

**Date:** 2026-06-20  
**Scope:** Phase 4C — three PixiJS warroom rooms replacing the existing `IsometricGrid`-based `Warroom.jsx`

---

## 1. Overview

Three visually distinct trading rooms rendered with PixiJS 7 (birds-eye top-down, Sensible Soccer style). Each room connects to the existing WebSocket feed for real trade/agent events. Agents are pixel sprites that react to backend events in real time.

Rooms are accessed via existing routes:
- `/warroom/long-term` → `WarroomLongTerm.jsx` → **The Bloomberg**
- `/warroom/swing` → `WarroomSwing.jsx` → **The Oak Office**  
- `/warroom/day-trading` → `WarroomDay.jsx` → **The Pit**

---

## 2. Visual Design

### 2A. The Bloomberg (Long-Term)
**Palette:** sky blue `#4a7eba`, gold `#D4AF37`, deep teal `#1A3A3A`  
**Background:** 35% city skyline (lit windows, varying heights) — cream checker tile floor below  
**Furniture:** 4 oak desks with Bloomberg terminal monitors + AABB collision zones  
**Plants:** 4 corner/wall plants (green circles, brown pots)  
**Agents:** 7 walking freely in aisles; dark suit colours; `speed=0.38`  
**Atmosphere:** subtle monitor glow flicker every ~210 frames; slow animated ticker (AAPL, MSFT, VOO, BRK.B, SPY)  
**Energy:** calm, professional

**Desk AABB collision zones (canvas 280×250, skyline cutoff ~87px):**
```
{x:12, y:107, w:72, h:24}   // left desk row 1
{x:12, y:153, w:72, h:24}   // left desk row 2
{x:96, y:125, w:70, h:28}   // center desk cluster
{x:184,y:107, w:86, h:66}   // right desk bank
{x:166,y:105, w:16, h:32}   // filing cabinet
```
`retarget()` resamples random point until no overlap (max 12 tries, fallback = room center).

### 2B. The Oak Office (Swing Trading)
**Palette:** amber `#CC8833`, copper `#B87333`, charcoal `#36454F`  
**Background:** wood plank floor (horizontal planks, alternating dark brown shades)  
**Walls:** dark wood panelling on left/right edges with amber groove lines  
**Ceiling:** 3 fluorescent ceiling light halos  
**Furniture:** 3 whiteboards (top wall) with line-art charts; 2 wall charts (right side); 6 desk stations (2 columns × 3 rows) with amber monitors and desk lamp  
**Agents:** 6, one per desk — `SeatedAgent` micro-wander ±6px from base position; `speed=0.25`  
**Atmosphere:** amber tint glow under each desk lamp; leather couch bottom-center  
**Energy:** focused, warm

### 2C. The Pit (Day Trading)
**Palette:** red `#FF3333`, green `#00FF00`, orange `#FF8C00`, near-black `#080404`  
**Background:** dark checker floor; crumpled paper ellipses scattered; 2 trash cans  
**Screen wall:** 5 trading screens top (0–50px) with bar charts, `BUY/SELL` labels, random flicker every ~40 frames  
**Furniture:** 3 rows of standing desks with LED indicators; all agents seated (micro-wander ±5px)  
**Agents:** 13, vested; vest colours cycle through team palette (11 distinct colours)  
**Chaos symbols:** `ChaosSymbol` objects orbit agent heads — spawn every 15 frames, symbols `▲▼!!$BUY⚡$$SELL%%%`, life 100–250 frames, elliptical orbit (r=14–22, ry=r×0.55), follow agent position  
**P&L overlay:** flickers between gain/loss values every ~75 frames  
**Countdown timer:** increments seconds in top-right  
**Energy:** chaotic, fast

---

## 3. Agent Architecture

### 3A. New files
```
frontend/src/components/Warroom/
  PixiWarroom.jsx          # PixiJS canvas wrapper (replaces IsometricGrid use inside Warroom)
  useWarroomAgents.js      # hook: fetch agents from store, map to PixiJS sprites
```

### 3B. Agent class hierarchy
```
Agent (base)
  ├── WalkingAgent         # Bloomberg — free walk + desk AABB avoidance
  └── SeatedAgent          # Oak + Pit — micro-wander from base pos
```

Both classes expose:
- `onTrade(symbol, action, pnl)` — show trade bubble, flash body colour
- `onProcessing()` — show spinner arc, spin for 90 frames
- `tick()` — called every frame by PIXI.ticker

### 3C. Agent sprite (all rooms)
- Body: oval (5×7), head: circle (r=3.5), shade-bar "sunglasses"  
- Leg: two small circles, animate on walk  
- `c.scale.x = dir` flips for left/right travel  
- Trade text: `Press Start 2P` 5px, anchor bottom-center, fade alpha last 30 frames  
- Spinner arc: 1.5π arc rotating above head while LLM processing  
- Flash: semi-transparent oval fill (green=gain, red=loss) over body, 22-frame decay  
- Click: toggle white ring around agent (inspector hook for Phase 4D)

---

## 4. Backend Integration

### 4A. WebSocket events consumed
All events already emitted by existing backend (`backend/main.py` lifespan scheduler, `websocket.store.js`).

| Event | Payload fields | Room action |
|-------|---------------|-------------|
| `trade_executed` | `agent_id, symbol, action, pnl` | Find sprite by `agent_id` → `onTrade(symbol, action, pnl)` |
| `agent_update` | `agent_id, status` | `status==="processing"` → `onProcessing()`; `status==="paused"` → gray tint |
| `portfolio_update` | `total_pnl, daily_pnl` | Update P&L overlay text |

### 4B. Agent data source
On mount: `GET /api/agents?room={room_key}` via `agentsApi.list({room})`.  
Map API agents to PixiJS agent sprites, distributing across spawn points / seat positions.  
Agents present in DB but not the current room are filtered out.

Room key mapping:
- `long_term` → Bloomberg (7 spawn points)
- `swing_trading` → Oak Office (6 seat positions)
- `day_trading` → The Pit (13 seat positions)

### 4C. Demo fallback
If no WebSocket events arrive within 3s of mount (dev/offline), demo mode activates: `tradeT` countdown fires random `onTrade` calls at room-appropriate cadence.  
Demo mode flag: `window.__LABOURIOUS_DEMO__ = true` (no backend dependency added).

---

## 5. File Map

### 5A. New files
| File | Purpose |
|------|---------|
| `frontend/src/components/Warroom/PixiWarroom.jsx` | PixiJS app wrapper; accepts `room` prop; owns canvas lifecycle |
| `frontend/src/components/Warroom/useWarroomAgents.js` | Hook: load agents from `agentsApi`, subscribe to WS store, map events to sprite callbacks |
| `frontend/src/components/Warroom/rooms/bloomberg.js` | Bloomberg background drawing + desk AABB data + spawn points |
| `frontend/src/components/Warroom/rooms/oak.js` | Oak Office background + seat positions |
| `frontend/src/components/Warroom/rooms/pit.js` | Pit background + seat positions + chaos symbol config |
| `frontend/src/components/Warroom/sprites/Agent.js` | Agent base class (PixiJS, no React) |
| `frontend/src/components/Warroom/sprites/WalkingAgent.js` | Extends Agent — free walk + AABB avoidance |
| `frontend/src/components/Warroom/sprites/SeatedAgent.js` | Extends Agent — micro-wander from base |
| `frontend/src/components/Warroom/sprites/ChaosSymbol.js` | Orbiting symbol (Pit only) |

### 5B. Modified files
| File | Change |
|------|--------|
| `frontend/src/pages/WarroomLongTerm.jsx` | Import `PixiWarroom`, render `<PixiWarroom room="long_term" />` |
| `frontend/src/pages/WarroomSwing.jsx` | Render `<PixiWarroom room="swing_trading" />` |
| `frontend/src/pages/WarroomDay.jsx` | Render `<PixiWarroom room="day_trading" />` |
| `frontend/package.json` | Add `pixi.js@^7.4.2` |

### 5C. Untouched files
`Warroom.jsx`, `IsometricGrid.jsx`, `AgentSprite.jsx`, `AgentInspector.jsx`, `TradeNotification.jsx`, `ApprovalDialog.jsx` — kept for Phase 4D compatibility. Pages switch renderer by importing `PixiWarroom` directly, not via `Warroom.jsx`.

---

## 6. Styling

- Canvas: `width:100%;height:auto;image-rendering:pixelated;display:block`  
- Container: `position:relative;border:2px solid <room-accent-color>;overflow:hidden`  
- Ticker bar: absolute bottom, `height:16px`, room accent background, `Press Start 2P` 4px font  
- P&L overlay: absolute top-left, semi-transparent background, `Press Start 2P` 5px  
- Scanlines: `repeating-linear-gradient(0deg, transparent 2px, rgba(0,0,0,0.08) 2px, ...)` overlay  
- Fonts: `Press Start 2P` (labels, headers) + `VT323` (ticker, body text)

---

## 7. Collision System

`WalkingAgent.retarget()`:
1. Pick random `(x, y)` within room bounds
2. Check against each desk AABB: `px+r > rx && px-r < rx+rw && py+r > ry && py-r < ry+rh`
3. If collision, resample (max 12 attempts, fallback = aisle center point)

`nudgeOut(agent, blocked)` called each frame:
- If agent center overlaps any AABB, push toward nearest edge at 3px/frame

Oak + Pit agents: no collision needed (seated, ±5–6px wander never reaches desk edges).

---

## 8. Performance Budget

| Metric | Target |
|--------|--------|
| Canvas size | 280×250px (scales via CSS) |
| Target FPS | 30 (PIXI ticker capped) |
| Max agents | 13 (Pit) |
| Chaos symbols | max ~20 alive at once (Pit) |
| WebSocket reconnect | existing store handles it |

PixiJS 7 renderer: WebGL with canvas fallback. `antialias: false` for pixel art sharpness.

---

## 9. Out of Scope

- User-controlled player character (requested but deferred — Phase 4D)
- Agent inspector panel wiring (Phase 4D — click handler stub only)
- Mobile touch support (Electron desktop only)
- Sound effects
- Phaser or other game engines (PixiJS only)
