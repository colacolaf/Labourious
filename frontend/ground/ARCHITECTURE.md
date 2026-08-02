# Architecture — Ground Floor Lobby (Minimal Edition)

How this minimal prototype mirrors deskrpg's runtime stack.

## deskrpg-stack mapping

| deskrpg concept               | This prototype                              | File             |
|-------------------------------|---------------------------------------------|------------------|
| `Phaser.Game({ pixelArt })`   | identical config + Arcade physics            | `scene.js`       |
| `BootScene.create()`          | identical — `generateAllTextures` then start | `scene.js`, `sprites.js` |
| `BootScene.drawTile` (16)     | verbatim 16-entry `drawTile` switch          | `sprites.js`     |
| `generateObjectTextures`      | identical canvas-flip + multiply-tint        | `sprites.js`     |
| `OBJECT_TYPES` registry       | verbatim port of `object-types.ts`           | `object-types.js`|
| Tile IDs (0/1/2/7/12)         | identical door-on-wall convention           | `layout.js`      |
| `MapData = { layers, objects }` | identical shape                             | `layout.js`      |
| BootScene → GameScene handoff | identical control flow                       | `scene.js`       |
| y-sort depth (`row * TILE`)   | identical, no overlay / no vignette          | `scene.js`       |

Pixel-for-pixel the artwork is deskrpg's; the runtime is deskrpg's; only
the file plumbing is reduced to a no-build single HTML page.

## Design decisions

### Wall structure

```
   ┌─────────────── ELEVATOR ────────┐
   │  ┌D┐ ▓ ┌D┐                       │   ← row 0 cols 13, 15 doors
   └──┴─┴─┴─┴─────────────────────┘
   
   ┌D┐                                  ┌D┐    ← row 7: doors to upper zone rooms
   │                                    │
   │              LOBBY                 │    ← central space, no furniture
   │             ┌───────┐             │       beyond 4 corner plants
   │             │LOBBY  │             │
   │             └───────┘             │
   │                                    │
   └D┐                                  ┌D┐    ← row 17: doors to lower zone rooms
   
   └────────────────────────────────────┘    ← row 23: closed south wall
```

- **Outer perimeter** on all four sides (rows 0/23 + cols 0/27) defines
  the rectangular lobby box.
- **4 doors** on the long sides — wall-layer tile-id 7 replacing the
  wall tile at col 0/27 rows 7 and 17. Each leads to one of the four
  ground-floor rooms (Research, Sentiment, Alt Data, Storage).
- **Elevator bank** on the top short end — two door tiles (row 0 cols 13
  + 15) flanking a centre pier, presenting two elevator bays.

### Objects

Just four corner plants (deskrpg plant sprite). Decoration-and-nothing-
else. No reception desk, no library, no workstations, no chairs, no
coffee, no water cooler — explicitly omitted because the brief asked for
"just a lobby".

### Signage

- **4 room plaques** hung at the row of each side door, just inside the
  wall. The plaques float over the underlying floor texture at setDepth
  1000 so they sit visually above the artwork.
- **Elevator directory** (`G · FLOORS 2-4 · PENTHOUSE`) hangs just south
  of the elevator bank.
- **`LOBBY` label** centred over the middle of the room, 11px font vs
  the 8px room plaques so it reads as the "name" of the floor.

### Why no overlays

deskrpg uses no lighting overlays, no vignettes, no decorative effects.
The Phaser.Game background-color is `#1a1a2e` (deskrpg's exact value)
and nothing else is drawn after the walls + objects layer. This keeps
the pixel grid as pure as the original.

### No NPCs

The lobby's narrative is told entirely through architecture and
typography — no figures, no receptionists, no bodyguards, no employees,
no visitors, no agents.
