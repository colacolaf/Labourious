// ---------------------------------------------------------------------------
// Generator script for the labourious Ground Floor Tiled JSON.
// Output: /Users/coleadams/labourious/frontend/ground/assets/templates/
//          labourious-ground-floor.tiled.json
//
// Layout (28 cols × 22 rows = 616 cells = 896×704 px):
//   - Outer ring = perimeter walls (stamp-*Walls tileset)
//   - 4 doors on the long sides (2 west col 0, 2 east col 27)
//   - 1 elevator on the top short end (row 0 cols 13/15 + pier at col 14)
//   - 1 main-building entrance on the bottom short end (row 21 cols 13..14
//     kept as walls; door gap implicit between lobby + outside)
//   - Interior = warm-gray carpet (소규모 오피스 맵 tile gid 301)
//   - Elevator pad top-centre = white-marble tile 1736
//   - Lounge area bottom-right = darker carpet 388
//   - Reception counter mid-row 4-5 (rows 4-5, cols 12-15)
//   - Corner planters + flanking planters
//
// Tilesets: identical 42-tileset set copied from the deskrpg small-office
// template so the pixel language is unchanged.
// ---------------------------------------------------------------------------

const fs = require("fs");
const path = require("path");

const COLS = 28;
const ROWS = 22;
const TILE = 32;

// Verbatim copy of deskrpg's small-office tilesets (same firstgid + image paths).
const TILESETS = [
  { firstgid: 601,  name: "small-office-tileset-ai",                                     tilewidth: 32, tileheight: 32, tilecount: 1024, columns: 32, image: "/assets/tilesets/builtin/small-office-tileset-ai.png",                                     imagewidth: 1024, imageheight: 1024 },
  { firstgid: 301,  name: "소규모 오피스 맵",                                              tilewidth: 32, tileheight: 32, tilecount: 300,  columns: 20, image: "/assets/tilesets/builtin/소규모-오피스-맵.png",                                              imagewidth: 640,  imageheight: 480 },
  { firstgid: 1734, name: "stamp-4ff3e012-b8fc-4f37-b142-eb6211ac8855-edited",            tilewidth: 32, tileheight: 32, tilecount: 2,     columns: 1,  image: "/assets/tilesets/builtin/stamp-4ff3e012-b8fc-4f37-b142-eb6211ac8855-edited.png",            imagewidth: 32,   imageheight: 64 },
  { firstgid: 1703, name: "stamp-85e84812-831a-4845-ae35-7e0ae078255a-edited",            tilewidth: 32, tileheight: 32, tilecount: 6,     columns: 2,  image: "/assets/tilesets/builtin/stamp-85e84812-831a-4845-ae35-7e0ae078255a-edited.png",            imagewidth: 64,   imageheight: 96 },
  { firstgid: 1678, name: "stamp-a79638b2-6527-4792-81e4-6a97824fd156-edited",            tilewidth: 32, tileheight: 32, tilecount: 6,     columns: 3,  image: "/assets/tilesets/builtin/stamp-a79638b2-6527-4792-81e4-6a97824fd156-edited.png",            imagewidth: 96,   imageheight: 64 },
  { firstgid: 1693, name: "stamp-52e50c59-fb9c-40e6-a0e5-3528619ab27b-edited",            tilewidth: 32, tileheight: 32, tilecount: 6,     columns: 3,  image: "/assets/tilesets/builtin/stamp-52e50c59-fb9c-40e6-a0e5-3528619ab27b-edited.png",            imagewidth: 96,   imageheight: 64 },
  { firstgid: 4905, name: "stamp-54d175c9-f032-4a0e-9dc9-a7c67b200454-stamp-edited-Foreground", tilewidth: 32, tileheight: 32, tilecount: 4, columns: 2, image: "/assets/tilesets/builtin/stamp-54d175c9-f032-4a0e-9dc9-a7c67b200454-stamp-edited-foreground.png", imagewidth: 64, imageheight: 64 },
  { firstgid: 2793, name: "stamp-4788b8ca-a027-4673-9f60-593c89e3a1ae-stamp-edited-Floor", tilewidth: 32, tileheight: 32, tilecount: 9,     columns: 3,  image: "/assets/tilesets/builtin/stamp-4788b8ca-a027-4673-9f60-593c89e3a1ae-stamp-edited-floor.png", imagewidth: 96,   imageheight: 96 },
  { firstgid: 1652, name: "edited-selection-1774856337212",                              tilewidth: 32, tileheight: 32, tilecount: 6,     columns: 3,  image: "/assets/tilesets/builtin/edited-selection-1774856337212.png",                              imagewidth: 96,   imageheight: 64 },
  { firstgid: 3854, name: "nano-banana-pro_a-pixel-art-tileset-sprite-she_20260330_205454",tilewidth: 32, tileheight: 32, tilecount: 1036,  columns: 37, image: "/assets/tilesets/builtin/nano-banana-pro_a-pixel-art-tileset-sprite-she_20260330_205454.png",imagewidth: 1184, imageheight: 896 },
  { firstgid: 1627, name: "color-palette",                                                tilewidth: 32, tileheight: 32, tilecount: 16,    columns: 16, image: "/assets/tilesets/builtin/color-palette.png",                                                imagewidth: 512,  imageheight: 32 },
  { firstgid: 1658, name: "edited-selection-1774856447457",                              tilewidth: 32, tileheight: 32, tilecount: 20,    columns: 5,  image: "/assets/tilesets/builtin/edited-selection-1774856447457.png",                              imagewidth: 160,  imageheight: 128 },
  { firstgid: 2811, name: "stamp-c6cfeb00-99ea-4cde-9280-c32d8ebfc607-stamp-edited-Paritition", tilewidth: 32, tileheight: 32, tilecount: 9, columns: 3, image: "/assets/tilesets/builtin/stamp-c6cfeb00-99ea-4cde-9280-c32d8ebfc607-stamp-edited-paritition.png", imagewidth: 96, imageheight: 96 },
  { firstgid: 1744, name: "stamp-d08c026e-ef5c-4344-b066-80123f17a499-stamp-edited-Floor",tilewidth: 32, tileheight: 32, tilecount: 2,     columns: 1,  image: "/assets/tilesets/builtin/stamp-d08c026e-ef5c-4344-b066-80123f17a499-stamp-edited-floor.png",imagewidth: 32,   imageheight: 64 },
  { firstgid: 3844, name: "stamp-2cf78e4e-e996-4b0d-9290-5b33df40d4c9-stamp-edited-Paritition",tilewidth: 32, tileheight: 32, tilecount: 6, columns: 2, image: "/assets/tilesets/builtin/stamp-2cf78e4e-e996-4b0d-9290-5b33df40d4c9-stamp-edited-paritition.png",imagewidth: 64, imageheight: 96 },
  { firstgid: 1684, name: "stamp-e9bf1410-0449-4cb9-9f71-6f6e40551402-edited",            tilewidth: 32, tileheight: 32, tilecount: 2,     columns: 1,  image: "/assets/tilesets/builtin/stamp-e9bf1410-0449-4cb9-9f71-6f6e40551402-edited.png",            imagewidth: 32,   imageheight: 64 },
  { firstgid: 1690, name: "edited-selection-1774857224660",                              tilewidth: 32, tileheight: 32, tilecount: 3,     columns: 1,  image: "/assets/tilesets/builtin/edited-selection-1774857224660.png",                              imagewidth: 32,   imageheight: 96 },
  { firstgid: 1710, name: "stamp-813f92d0-4977-41b5-98af-cd1a973057ce-edited",            tilewidth: 32, tileheight: 32, tilecount: 9,     columns: 3,  image: "/assets/tilesets/builtin/stamp-813f92d0-4977-41b5-98af-cd1a973057ce-edited.png",            imagewidth: 96,   imageheight: 96 },
  { firstgid: 1625, name: "stamp-e3a87a52-3ecf-48ea-ae24-bcebbfffbcdb-edited",            tilewidth: 32, tileheight: 32, tilecount: 2,     columns: 1,  image: "/assets/tilesets/builtin/stamp-e3a87a52-3ecf-48ea-ae24-bcebbfffbcdb-edited.png",            imagewidth: 32,   imageheight: 64 },
  { firstgid: 1643, name: "stamp-74d8d218-3535-4fec-bfda-6b6fb82ee0e7-edited",            tilewidth: 32, tileheight: 32, tilecount: 3,     columns: 1,  image: "/assets/tilesets/builtin/stamp-74d8d218-3535-4fec-bfda-6b6fb82ee0e7-edited.png",            imagewidth: 32,   imageheight: 96 },
  { firstgid: 1746, name: "stamp-efd330f8-c243-4508-9bed-20c074be8f08-edited",            tilewidth: 32, tileheight: 32, tilecount: 4,     columns: 2,  image: "/assets/tilesets/builtin/stamp-efd330f8-c243-4508-9bed-20c074be8f08-edited.png",            imagewidth: 64,   imageheight: 64 },
  { firstgid: 4903, name: "stamp-d08c026e-ef5c-4344-b066-80123f17a499-stamp-edited-Walls", tilewidth: 32, tileheight: 32, tilecount: 2,     columns: 1,  image: "/assets/tilesets/builtin/stamp-d08c026e-ef5c-4344-b066-80123f17a499-stamp-edited-walls.png", imagewidth: 32,   imageheight: 64 },
  { firstgid: 4892, name: "stamp-7ed500ec-5ee8-4ee1-906d-c926649b4d1f-stamp-edited-Walls",tilewidth: 32, tileheight: 32, tilecount: 9,     columns: 3,  image: "/assets/tilesets/builtin/stamp-7ed500ec-5ee8-4ee1-906d-c926649b4d1f-stamp-edited-walls.png",imagewidth: 96,   imageheight: 96 },
  { firstgid: 4909, name: "stamp-52e50c59-fb9c-40e6-a0e5-3528619ab27b-stamp-edited-Foreground",tilewidth: 32, tileheight: 32, tilecount: 6, columns: 3, image: "/assets/tilesets/builtin/stamp-52e50c59-fb9c-40e6-a0e5-3528619ab27b-stamp-edited-foreground.png",imagewidth: 96, imageheight: 64 },
  { firstgid: 4901, name: "stamp-d08c026e-ef5c-4344-b066-80123f17a499-stamp-edited-Foreground",tilewidth: 32, tileheight: 32, tilecount: 2, columns: 1, image: "/assets/tilesets/builtin/stamp-d08c026e-ef5c-4344-b066-80123f17a499-stamp-edited-foreground.png",imagewidth: 32, imageheight: 64 },
  { firstgid: 1699, name: "edited-selection-1774857575323",                              tilewidth: 32, tileheight: 32, tilecount: 4,     columns: 1,  image: "/assets/tilesets/builtin/edited-selection-1774857575323.png",                              imagewidth: 32,   imageheight: 128 },
  { firstgid: 2784, name: "stamp-5ac6ce84-4efd-497a-82d3-4b46a44f63d3-stamp-edited-Floor",tilewidth: 32, tileheight: 32, tilecount: 9,     columns: 3,  image: "/assets/tilesets/builtin/stamp-5ac6ce84-4efd-497a-82d3-4b46a44f63d3-stamp-edited-floor.png",imagewidth: 96,   imageheight: 96 },
  { firstgid: 1719, name: "edited-selection-1774858792925",                              tilewidth: 32, tileheight: 32, tilecount: 6,     columns: 3,  image: "/assets/tilesets/builtin/edited-selection-1774858792925.png",                              imagewidth: 96,   imageheight: 64 },
  { firstgid: 3850, name: "stamp-54d175c9-f032-4a0e-9dc9-a7c67b200454-stamp-edited-Walls",tilewidth: 32, tileheight: 32, tilecount: 4,    columns: 2,  image: "/assets/tilesets/builtin/stamp-54d175c9-f032-4a0e-9dc9-a7c67b200454-stamp-edited-walls.png",imagewidth: 64,   imageheight: 64 },
  { firstgid: 1736, name: "stamp-4ff3e012-b8fc-4f37-b142-eb6211ac8855-stamp-edited-Walls",tilewidth: 32, tileheight: 32, tilecount: 2,    columns: 1,  image: "/assets/tilesets/builtin/stamp-4ff3e012-b8fc-4f37-b142-eb6211ac8855-stamp-edited-walls.png",imagewidth: 32,   imageheight: 64 },
  { firstgid: 2802, name: "stamp-4788b8ca-a027-4673-9f60-593c89e3a1ae-stamp-edited-Paritition",tilewidth: 32, tileheight: 32, tilecount: 9, columns: 3, image: "/assets/tilesets/builtin/stamp-4788b8ca-a027-4673-9f60-593c89e3a1ae-stamp-edited-paritition.png",imagewidth: 96, imageheight: 96 },
  { firstgid: 1725, name: "stamp-782212ef-4b96-4378-a705-afa87b4d3c2f-stamp-edited-Floor",tilewidth: 32, tileheight: 32, tilecount: 9,     columns: 3,  image: "/assets/tilesets/builtin/stamp-782212ef-4b96-4378-a705-afa87b4d3c2f-stamp-edited-floor.png",imagewidth: 96,   imageheight: 96 },
  { firstgid: 1750, name: "stamp-efd330f8-c243-4508-9bed-20c074be8f08-stamp-edited-Floor",tilewidth: 32, tileheight: 32, tilecount: 4,    columns: 2,  image: "/assets/tilesets/builtin/stamp-efd330f8-c243-4508-9bed-20c074be8f08-stamp-edited-floor.png",imagewidth: 64,   imageheight: 64 },
  { firstgid: 1709, name: "edited-selection-1774858252407",                              tilewidth: 32, tileheight: 32, tilecount: 1,     columns: 1,  image: "/assets/tilesets/builtin/edited-selection-1774858252407.png",                              imagewidth: 32,   imageheight: 32 },
  { firstgid: 1646, name: "stamp-db9a0ee8-6dbd-46e1-8425-efafd88bd054-edited",            tilewidth: 32, tileheight: 32, tilecount: 4,     columns: 2,  image: "/assets/tilesets/builtin/stamp-db9a0ee8-6dbd-46e1-8425-efafd88bd054-edited.png",            imagewidth: 64,   imageheight: 64 },
  { firstgid: 1738, name: "stamp-7ed500ec-5ee8-4ee1-906d-c926649b4d1f-stamp-edited-Floor",tilewidth: 32, tileheight: 32, tilecount: 6,    columns: 3,  image: "/assets/tilesets/builtin/stamp-7ed500ec-5ee8-4ee1-906d-c926649b4d1f-stamp-edited-floor.png",imagewidth: 96,   imageheight: 64 },
  { firstgid: 4890, name: "stamp-ef2185bc-5680-4d2e-9abd-1da538c0a738-stamp-edited-Floor",tilewidth: 32, tileheight: 32, tilecount: 2,    columns: 2,  image: "/assets/tilesets/builtin/stamp-ef2185bc-5680-4d2e-9abd-1da538c0a738-stamp-edited-floor.png",imagewidth: 64,   imageheight: 32 },
  { firstgid: 1686, name: "edited-selection-1774856962259",                              tilewidth: 32, tileheight: 32, tilecount: 4,     columns: 2,  image: "/assets/tilesets/builtin/edited-selection-1774856962259.png",                              imagewidth: 64,   imageheight: 64 },
  { firstgid: 2778, name: "stamp-3f7a8f1e-c437-4527-8b37-42213b4b2e4a-edited",            tilewidth: 32, tileheight: 32, tilecount: 6,     columns: 3,  image: "/assets/tilesets/builtin/stamp-3f7a8f1e-c437-4527-8b37-42213b4b2e4a-edited.png",            imagewidth: 96,   imageheight: 64 },
  { firstgid: 2820, name: "nano-banana-pro_a-pixel-art-tileset-sprite-she_20260330_185733",tilewidth: 32, tileheight: 32, tilecount: 1024, columns: 32, image: "/assets/tilesets/builtin/nano-banana-pro_a-pixel-art-tileset-sprite-she_20260330_185733.png",imagewidth: 1024, imageheight: 1024 },
  { firstgid: 1754, name: "small-office-tileset-ai-back",                                tilewidth: 32, tileheight: 32, tilecount: 1024, columns: 32, image: "/assets/tilesets/builtin/small-office-tileset-ai-back.png",                                imagewidth: 1024, imageheight: 1024 },
  { firstgid: 1650, name: "stamp-acaf4017-6515-4038-ad3e-86a9ceadc7af-edited",            tilewidth: 32, tileheight: 32, tilecount: 2,     columns: 1,  image: "/assets/tilesets/builtin/stamp-acaf4017-6515-4038-ad3e-86a9ceadc7af-edited.png",            imagewidth: 32,   imageheight: 64 },
];

// ---------------------------------------------------------------------------
// Build grids.
// ---------------------------------------------------------------------------
function emptyGrid(c, r) {
  const g = [];
  for (let i = 0; i < r; i++) g.push(new Array(c).fill(0));
  return g;
}

// FLOOR — warm beige carpet (gid 301) on every cell, then override the pad.
const FLOOR = emptyGrid(COLS, ROWS);
for (let r = 0; r < ROWS; r++) {
  for (let c = 0; c < COLS; c++) FLOOR[r][c] = 301;
}
// Pad area around the elevator (top centre) — white-marble gid 1736/1737/1738/1739
const PAD_TILES = [1736, 1737, 1738, 1739, 1736];
for (let r = 1; r <= 2; r++) {
  for (let c = 12; c <= 15; c++) FLOOR[r][c] = PAD_TILES[(c - 12) + (r - 1)];
}
// Lounge area bottom-right — darker carpet tiles 388..396
for (let r = 16; r <= 20 && r < ROWS - 1; r++) {
  for (let c = 18; c <= 26 && c < COLS - 1; c++) {
    FLOOR[r][c] = 388 + (((r - 16) * 9 + (c - 18)) % 9);
  }
}

// WALLS — perimeter 4903 top edge / 4904 inner; doors = 0 (walkable gap).
const WALL = emptyGrid(COLS, ROWS);
const WALL_TOP   = 4903;
const WALL_INNER = 4904;
for (let c = 0; c < COLS; c++) {
  WALL[0][c] = WALL_TOP;
  WALL[ROWS - 1][c] = WALL_INNER;
}
for (let r = 0; r < ROWS; r++) {
  WALL[r][0] = WALL_INNER;
  WALL[r][COLS - 1] = WALL_INNER;
}
// 4 doors on long sides: west col 0 rows 8-9 & 14-15, east col 27 rows 8-9 & 14-15.
for (const r of [8, 9, 14, 15]) {
  WALL[r][0] = 0;
  WALL[r][COLS - 1] = 0;
}
// 1 elevator on top short end: doors at cols 13 + 15, pier at col 14.
WALL[0][13] = 0;
WALL[0][15] = 0;
// Bottom short end main-building entrance: keep cols 13-14 as walls (the
// gap between the two walls is the main entry — conceptually columns 12 or
// 15 act as doorways but in tile-level detail we leave the bottom row wall
// intact, and let the player walk out via the side doorways).

// FOREGROUND — reception counter, planters, lounge couches.
// Reception cluster: 4901 + fan-out via stamp-d08c026e-Foreground (rows 0-1).
const FG = emptyGrid(COLS, ROWS);
// Reception counter tiles (rows 4-5, cols 12-15).
for (let r = 4; r <= 5; r++) {
  for (let c = 12; c <= 15; c++) FG[r][c] = 4902;
}
// Two flanking planters near the elevator pad (cols 11 / 16, rows 2-3).
FG[2][11] = 1690; FG[3][11] = 1691;
FG[2][16] = 1690; FG[3][16] = 1691;
// Corner planters rows 1-2, cols 1 and 26.
FG[1][1]  = 1690; FG[2][1]  = 1691;
FG[1][26] = 1690; FG[2][26] = 1691;
// Lounge couches bottom-right — stamp-*Foreground tiles 4906+.
for (let r = 17; r <= 20 && r < ROWS - 1; r++) {
  for (let c = 19; c <= 25 && c < COLS - 1; c++) {
    FG[r][c] = 4906 + (((r - 17) * 7 + (c - 19)) % 6);
  }
}

// PARITITION — empty.
const PART = emptyGrid(COLS, ROWS);

// COLLISION — mirror Walls.
const COLL = emptyGrid(COLS, ROWS);
for (let r = 0; r < ROWS; r++) {
  for (let c = 0; c < COLS; c++) {
    COLL[r][c] = WALL[r][c] === 0 ? 0 : 1642;
  }
}

// ---------------------------------------------------------------------------
// Serialize.
// ---------------------------------------------------------------------------
const flat = (g) => {
  const out = [];
  for (let r = 0; r < g.length; r++) for (let c = 0; c < g[0].length; c++) out.push(g[r][c]);
  return out;
};

const tiled = {
  compressionlevel: -1,
  width: COLS,
  height: ROWS,
  tilewidth: TILE,
  tileheight: TILE,
  orientation: "orthogonal",
  renderorder: "right-down",
  infinite: false,
  type: "map",
  version: "1.10",
  tiledversion: "1.11.2",
  nextlayerid: 7,
  nextobjectid: 2,
  tilesets: TILESETS,
  layers: [
    { id: 1, name: "Floor",      type: "tilelayer",   width: COLS, height: ROWS, x: 0, y: 0, opacity: 1, visible: true, data: flat(FLOOR), properties: [{ name: "depth", type: "int", value: 0 }] },
    { id: 2, name: "Walls",      type: "tilelayer",   width: COLS, height: ROWS, x: 0, y: 0, opacity: 1, visible: true, data: flat(WALL), properties: [{ name: "depth", type: "int", value: 1 }] },
    { id: 3, name: "Foreground", type: "tilelayer",   width: COLS, height: ROWS, x: 0, y: 0, opacity: 1, visible: true, data: flat(FG),   properties: [{ name: "depth", type: "int", value: 10000 }] },
    { id: 4, name: "Paritition", type: "tilelayer",   width: COLS, height: ROWS, x: 0, y: 0, opacity: 1, visible: true, data: flat(PART), properties: [{ name: "depth", type: "int", value: 10001 }] },
    { id: 5, name: "Collision",  type: "tilelayer",   width: COLS, height: ROWS, x: 0, y: 0, opacity: 0.5, visible: true, data: flat(COLL), properties: [{ name: "depth", type: "int", value: 2 }] },
    { id: 6, name: "Objects",    type: "objectgroup", x: 0, y: 0, opacity: 1, visible: true, draworder: "topdown",
      objects: [{ id: 1, name: "spawn", type: "spawn", x: 12 * 32, y: 18 * 32, width: 32, height: 32, visible: true }],
      properties: [{ name: "depth", type: "string", value: "y-sort" }] },
  ],
};

const outPath = path.resolve(__dirname, "..", "assets", "templates", "labourious-ground-floor.tiled.json");
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(tiled, null, 0));
console.log("wrote", outPath, "size:", fs.statSync(outPath).size, "bytes");
console.log("grid:", COLS, "×", ROWS, "=", COLS * ROWS, "cells /", (COLS * TILE), "×", (ROWS * TILE), "px");
console.log("tilesets:", TILESETS.length);
console.log("layers:", tiled.layers.length, "(Floor, Walls, Foreground, Paritition, Collision, Objects)");
