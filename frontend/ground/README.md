# Labourious — Ground Floor Lobby (Prototype)

First-pass prototype of the Ground Floor Lobby of the Labourious building.

**In the most simple terms**: just a lobby. Four room doors on the long
sides (two per side). One elevator at the top short end. Clean brass
typography on a deskrpg-faithful pixel grid.

The prototype is a single-page Phaser 3 app rendered with **the same
runtime pipeline as deskrpg** — pixel art generated procedurally in
`BootScene` via Phaser.Graphics → generateTexture, then composited into
a 28 × 24 tile grid (TILE = 32 px) using deskrpg's
`MapData = { layers: { floor, walls }, objects }` shape.

## Running

```bash
cd frontend/ground
python3 -m http.server 8080
# then open http://localhost:8080/
```

ES modules require `http://` — opening `index.html` via `file://` will not
work in modern browsers.

## What it shows

- **Closed rectangular lobby** — 28 × 24 cells, perimeter walls on all
  four sides, no interior partitions.
- **4 room doors**: two on the left wall (rows 7 + 17), two mirror on the
  right wall (rows 7 + 17). Each is a deskrpg wall-layer door tile.
- **1 elevator bank on the top short end**: two doors at row 0 cols 13 & 15
  with a centre pier between them.
- **4 corner plants** — deskrpg plant sprites, minimum decor only.
- **Brass typography plaques**: `RESEARCH` / `SENTIMENT` / `ALT · DATA` /
  `STORAGE` next to each side door, an elevator directory strip near the
  top, a `LOBBY` label at the centre.
- **No NPCs** of any kind. No figures, no reception, no library, no
  workstations. The lobby's narrative is told entirely through walls +
  doors + typography.

## File map

```
frontend/ground/
├── index.html              ← Phaser 3.90 CDN, mounts ./src/lib/scene.js
├── ARCHITECTURE.md
└── src/lib/
    ├── palette.js          ← deskrpg-exact color tokens
    ├── object-types.js     ← OBJECT_TYPES registry + tile-id constants
    ├── sprites.js          ← 16-tile spritesheet + 11 object textures
    ├── layout.js           ← 28×24 MapData (closed rectangle + 4 doors + 1 elevator + 4 plants)
    └── scene.js            ← BootScene + GameScene + brass plaques
```

All sprites are generated at runtime — no PNG / SVG assets are downloaded.
