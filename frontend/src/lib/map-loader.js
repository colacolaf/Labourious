// Loads a room MapData JSON into a Phaser scene: paints floor/wall tile layers, places
// object graphics with y-sort depth, and returns spawn/agent-slot anchor points.
//
// No Phaser import needed here — every Phaser API used (scene.add.*, scene.textures.*) comes
// through the `scene` instance passed in, so this file stays free of the jsdom+Phaser import
// crash and is safe to pull into unit tests.
//
// MapData shape (frozen spec, docs/superpowers/specs/2026-07-04-deskrpg-redesign-design.md):
// {
//   name, roomKey, theme: "investment" | "sector" | "cubicle",
//   layers: { floor: number[30][40], walls: number[30][40] },  // tile index, 0 = empty
//   objects: [{ id, type, col, row, direction? }],
//   agentSlots: [{ id, col, row, facing }],
//   metadata: { spawnCol, spawnRow, cameraCenter: { col, row } },
// }
import { getObjectFootprint } from './object-types';

export const TILE_SIZE = 32;

// Tile index -> palette key (see spec's tile index table). 0 (EMPTY) is never painted.
const TILE_KEY_BY_INDEX = { 1: 'floor', 2: 'wall', 7: 'door', 12: 'carpet' };

const PALETTES = {
  investment: { floor: 0x8b8378, wall: 0x4a4a5e, door: 0xa39a8c, carpet: 0x7a7368 },
  sector: { floor: 0xf5f5f5, wall: 0xffffff, door: 0xffffff, carpet: 0xeeeeee },
  cubicle: { floor: 0x6b7280, wall: 0x9ca3af, door: 0x3b82f6, carpet: 0x5b6370 },
};
const DEFAULT_PALETTE = PALETTES.investment;

const OBJECT_COLORS = {
  desk: 0x8b5e3c,
  chair: 0x6b4423,
  computer: 0x334155,
  plant: 0x2f855a,
  bookshelf: 0x78350f,
  meeting_table: 0x92400e,
  coffee: 0x451a03,
  water_cooler: 0x60a5fa,
  whiteboard: 0xffffff,
  reception_desk: 0xb45309,
  cubicle_wall: 0x888899,
  paper_stack: 0xe5e7eb,
  sector_poster: 0xd97706,
  monitor_wall: 0x3b82f6,
};
const DEFAULT_OBJECT_COLOR = 0x999999;

function tileCenter(col, row) {
  return { x: col * TILE_SIZE + TILE_SIZE / 2, y: row * TILE_SIZE + TILE_SIZE / 2 };
}

// ponytail: office.png / real tileset frames don't exist yet (later task). If the tileset
// texture happens to be loaded we drop a plain image per tile; otherwise (today, always)
// fall back to a flat colored rect from the palette table. Either way this never crashes.
function paintTile(scene, col, row, color, hasTileset, tilesetKey, depth) {
  const { x, y } = tileCenter(col, row);
  const obj = hasTileset
    ? scene.add.image(x, y, tilesetKey).setDisplaySize(TILE_SIZE, TILE_SIZE)
    : scene.add.rectangle(x, y, TILE_SIZE, TILE_SIZE, color);
  obj.setDepth(depth);
  return obj;
}

function paintTileLayer(scene, tiles, palette, hasTileset, tilesetKey, depthForRow) {
  (tiles || []).forEach((rowTiles, row) => {
    (rowTiles || []).forEach((index, col) => {
      if (!index) return; // 0 = EMPTY, nothing to paint
      const key = TILE_KEY_BY_INDEX[index];
      if (!key) {
        console.warn(`[map-loader] unrecognized tile index ${index} at col ${col}, row ${row} — falling back to floor color`);
      }
      const color = palette[key] ?? palette.floor;
      paintTile(scene, col, row, color, hasTileset, tilesetKey, depthForRow(row));
    });
  });
}

function placeObjects(scene, objects) {
  for (const obj of objects || []) {
    const { w, h } = getObjectFootprint(obj.type);
    const width = w * TILE_SIZE;
    const height = h * TILE_SIZE;
    const x = obj.col * TILE_SIZE + width / 2;
    const y = obj.row * TILE_SIZE + height / 2;
    const color = OBJECT_COLORS[obj.type] ?? DEFAULT_OBJECT_COLOR;
    const rect = scene.add.rectangle(x, y, width - 2, height - 2, color);
    rect.setDepth(obj.row); // basic y-sort
  }
}

/**
 * Paints `mapData` into `scene` and returns spawn/seat anchor points in pixel space.
 * @param {Phaser.Scene} scene
 * @param {object} mapData - parsed MapData JSON (see shape above)
 * @param {string} tilesetKey - texture key for the tileset (may not be loaded yet)
 * @returns {{ spawnPoints: {x:number,y:number}[], seatMap: Record<string,{x:number,y:number}> }}
 */
export function loadMapIntoScene(scene, mapData, tilesetKey) {
  const palette = PALETTES[mapData?.theme] || DEFAULT_PALETTE;
  const hasTileset = Boolean(scene?.textures?.exists?.(tilesetKey));

  paintTileLayer(scene, mapData?.layers?.floor, palette, hasTileset, tilesetKey, () => -2);
  paintTileLayer(scene, mapData?.layers?.walls, palette, hasTileset, tilesetKey, (row) => row);
  placeObjects(scene, mapData?.objects);

  const metadata = mapData?.metadata || {};
  const spawnPoints = [];
  if (Number.isFinite(metadata.spawnCol) && Number.isFinite(metadata.spawnRow)) {
    spawnPoints.push(tileCenter(metadata.spawnCol, metadata.spawnRow));
  }

  const seatMap = {};
  for (const slot of mapData?.agentSlots || []) {
    seatMap[slot.id] = tileCenter(slot.col, slot.row);
  }

  return { spawnPoints, seatMap };
}
