// object-types.js
// ---------------------------------------------------------------------------
// Verbatim port of deskrpg's src/lib/object-types.ts.
//
// Defines the canonical Object Type System used across deskrpg maps:
//  - 11 object types with width / height / collision / depthMode fields
//  - Floor tile IDs (0 = EMPTY, 1 = FLOOR, 12 = CARPET)
//  - Wall tile IDs (2 = WALL, 7 = DOOR)
//  - getObjectDimensions() with the direction-swaps-width/height rule
//  - computeOccupiedTiles() and canPlaceObject() for layout validation
//
// Mirroring deskrpg's API verbatim means our GameScene can ingest the same
// MapData shape and render every object with the same depth / collision
// guarantees as the upstream engine.
// ---------------------------------------------------------------------------

export const TILE = 32; // pixels — matches deskrpg BootScene

// ---------------------------------------------------------------------------
// Object types
// ---------------------------------------------------------------------------

export const OBJECT_TYPES = {
  desk:           { id: "desk",           name: "Desk",           width: 1, height: 1, collision: true,  renderType: "graphic", depthMode: "y-sort", directional: true },
  chair:          { id: "chair",          name: "Chair",          width: 1, height: 1, collision: false, renderType: "graphic", depthMode: "y-sort", directional: true },
  computer:       { id: "computer",       name: "Computer",       width: 1, height: 1, collision: false, renderType: "graphic", depthMode: "y-sort", directional: true },
  plant:          { id: "plant",          name: "Plant",          width: 1, height: 1, collision: true,  renderType: "graphic", depthMode: "y-sort", directional: true },
  bookshelf:      { id: "bookshelf",      name: "Bookshelf",      width: 1, height: 1, collision: true,  renderType: "graphic", depthMode: "fixed", fixedDepth: 5, directional: true },
  meeting_table:  { id: "meeting_table",  name: "Meeting Table",  width: 2, height: 2, collision: true,  renderType: "graphic", depthMode: "y-sort", directional: true },
  coffee:         { id: "coffee",         name: "Coffee Machine", width: 1, height: 1, collision: true,  renderType: "graphic", depthMode: "y-sort", directional: true },
  water_cooler:   { id: "water_cooler",   name: "Water Cooler",   width: 1, height: 1, collision: true,  renderType: "graphic", depthMode: "y-sort", directional: true },
  whiteboard:     { id: "whiteboard",     name: "Whiteboard",     width: 1, height: 1, collision: true,  renderType: "graphic", depthMode: "fixed", fixedDepth: 5, directional: true },
  reception_desk: { id: "reception_desk", name: "Reception Desk", width: 2, height: 1, collision: true,  renderType: "graphic", depthMode: "y-sort", directional: true },
  cubicle_wall:   { id: "cubicle_wall",   name: "Cubicle Wall",   width: 1, height: 1, collision: true,  renderType: "graphic", depthMode: "y-sort", directional: true },
};

export const OBJECT_TYPE_LIST = Object.values(OBJECT_TYPES);

// ---------------------------------------------------------------------------
// Effective width / height (left / right swap w and h for non-square objects)
// ---------------------------------------------------------------------------
export function getObjectDimensions(type, direction) {
  const def = OBJECT_TYPES[type];
  if (!def) return { width: 1, height: 1 };
  const w = def.width || 1;
  const h = def.height || 1;
  if ((direction === "left" || direction === "right") && w !== h) {
    return { width: h, height: w };
  }
  return { width: w, height: h };
}

// ---------------------------------------------------------------------------
// Tile IDs (deskrpg GameScene convention)
// ---------------------------------------------------------------------------
export const FLOOR_TILE_IDS = new Set([0, 1, 12]); // EMPTY, FLOOR, CARPET
export const WALL_TILE_IDS  = new Set([2, 7]);     // WALL, DOOR

// Tile-id enum (deskrpg GameScene: tile values stored in floor[][] + walls[][]).
// Named TILE_ID (not TILE) to avoid colliding with the pixel-size constant
// declared up top — duplicate `const TILE` was a real browser bug.
export const TILE_ID = Object.freeze({
  EMPTY: 0,
  FLOOR: 1,
  WALL:  2,
  DOOR:  7,
  CARPET:12,
});

// ---------------------------------------------------------------------------
// Object ID generation (matches deskrpg's generateObjectId)
// ---------------------------------------------------------------------------
let objectIdCounter = 0;
export function generateObjectId() {
  return `obj-${Date.now().toString(36)}-${(objectIdCounter++).toString(36)}`;
}

// ---------------------------------------------------------------------------
// Occupied tiles computation (collision footprints only)
// ---------------------------------------------------------------------------
export function computeOccupiedTiles(objects) {
  const occupied = new Set();
  for (const obj of objects) {
    const def = OBJECT_TYPES[obj.type];
    if (!def || !def.collision) continue;
    const { width: w, height: h } = getObjectDimensions(obj.type, obj.direction);
    for (let c = obj.col; c < obj.col + w; c++) {
      for (let r = obj.row; r < obj.row + h; r++) {
        occupied.add(`${c},${r}`);
      }
    }
  }
  return occupied;
}

// ---------------------------------------------------------------------------
// Stacking / wall validation (matches deskrpg canPlaceObject)
// ---------------------------------------------------------------------------
export function canPlaceObject(type, col, row, existingObjects, wallsData, direction) {
  const def = OBJECT_TYPES[type];
  if (!def) return false;
  const { width: w, height: h } = getObjectDimensions(type, direction);

  for (let c = col; c < col + w; c++) {
    for (let r = row; r < row + h; r++) {
      if (wallsData?.[r]?.[c] === TILE_ID.WALL) return false;
      if (def.collision) {
        for (const obj of existingObjects) {
          const oDef = OBJECT_TYPES[obj.type];
          if (!oDef || !oDef.collision) continue;
          const { width: ow, height: oh } = getObjectDimensions(obj.type, obj.direction);
          if (c >= obj.col && c < obj.col + ow && r >= obj.row && r < obj.row + oh) {
            return false;
          }
        }
      }
    }
  }
  return true;
}
