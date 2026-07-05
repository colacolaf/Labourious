// Furniture/room object type constants and tile-occupancy helpers.
// Pure data/logic — no Phaser dependency, so this stays safe to import from unit tests.

export const OBJECT_TYPES = Object.freeze([
  'desk',
  'chair',
  'computer',
  'plant',
  'bookshelf',
  'meeting_table',
  'coffee',
  'water_cooler',
  'whiteboard',
  'reception_desk',
  'cubicle_wall',
  'paper_stack',
  'sector_poster',
  'monitor_wall',
]);

// Tile footprint (cols x rows) for object types that occupy more than one tile.
// Everything not listed here defaults to 1x1 (see getObjectFootprint).
const FOOTPRINTS = {
  meeting_table: { w: 2, h: 2 },
};

const DEFAULT_FOOTPRINT = { w: 1, h: 1 };

export function getObjectFootprint(type) {
  return FOOTPRINTS[type] || DEFAULT_FOOTPRINT;
}

/**
 * Given placed objects `{ id, type, col, row }`, returns a Set of "col,row" strings
 * for every tile they occupy (accounting for multi-tile footprints like meeting_table).
 */
export function computeOccupiedTiles(objects) {
  const occupied = new Set();
  for (const obj of objects || []) {
    const { w, h } = getObjectFootprint(obj.type);
    for (let dc = 0; dc < w; dc++) {
      for (let dr = 0; dr < h; dr++) {
        occupied.add(`${obj.col + dc},${obj.row + dr}`);
      }
    }
  }
  return occupied;
}
