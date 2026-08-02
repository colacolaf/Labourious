// ---------------------------------------------------------------------------
// layout.js — Minimal Labourious ground-floor lobby layout.
//
// Tile-IDs use deskrpg's EXACT conventions (see BootScene.ts line 87). The
// strip "office-tiles" exposes one frame per ID:
//   0 empty | 1 floor | 2 wall | 3 desk | 4 chair | 5 computer | 6 plant |
//   7 door | 8 meeting | 9 coffee | 10 cooler | 11 bookshelf | 12 carpet |
//  13 whiteboard | 14 reception | 15 cubicle
//
// Shape: a single clean rectangle, 28 cols × 24 rows. Outer wall perimeter
// on every edge, with FIVE deskrpg doors cut into the perimeter:
//   • Two on long side col 0   (entering the room on the left)
//   • Two on long side col 27  (entering the room on the right)
//   • One elevator door at row 0, col 14 (entering on top)
// No interior subdivision — this is a lobby, not offices.
// ---------------------------------------------------------------------------

import { TILE_ID as T } from "./sprites.js";

export const COLS = 28;
export const ROWS = 24;

// Build the floor + walls grid: 0 = empty, 1 = walkable floor, 2 = wall.
function buildGrid() {
  const grid = [];
  for (let r = 0; r < ROWS; r++) {
    const row = [];
    for (let c = 0; c < COLS; c++) row.push(T.WALL);
    grid.push(row);
  }

  // Fill the interior with floor (warm gray carpet).
  for (let r = 1; r < ROWS - 1; r++) {
    for (let c = 1; c < COLS - 1; c++) grid[r][c] = T.FLOOR;
  }

  // Five doors (deskrpg tile-id 7) — replacing the wall block at these cells.
  // Each door is 1 wide × 2 tall (deskrpg convention).
  const doors = [
    [7,  0], [8,  0],   // left side, upper pair
    [17, 0], [18, 0],   // left side, lower pair
    [7, 27],  [8, 27],  // right side, upper pair
    [17, 27], [18, 27], // right side, lower pair
  ];
  for (const [r, c] of doors) grid[r][c] = T.DOOR;

  // One elevator door at the top short end (centre, two leaves + a pier).
  grid[0][13] = T.DOOR;
  grid[0][15] = T.DOOR;
  // Col 14 stays WALL (the pier between the two elevator doors).

  return grid;
}

export const GRID = buildGrid();

// Build the wall-on-top mask: a single 28×24 grid of booleans. The render
// loop draws a TILE_ID.WALL at every position where the cell collides.
export const COLLISION = GRID.map((row) =>
  row.map((cell) => cell === T.WALL || cell === T.DOOR ? 1 : 0)
);

// Object placements (rendered after the floor + walls).
// Only 4 plants at the four interior corners, exactly mirroring deskrpg's
// default Lobby seed.
export const OBJECTS = [
  { type: "plant", col: 2,  row: 2  },
  { type: "plant", col: 25, row: 2  },
  { type: "plant", col: 2,  row: 21 },
  { type: "plant", col: 25, row: 21 },
];

export const MAP = {
  cols: COLS,
  rows: ROWS,
  tile: T.WALL, // exported for dependents (legacy alias)
};
