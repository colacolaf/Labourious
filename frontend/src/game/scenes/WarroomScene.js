import Phaser from 'phaser';
import { EventBus } from '../EventBus';
import { loadMapIntoScene, TILE_SIZE } from '../../lib/map-loader';

const MAP_COLS = 40;
const MAP_ROWS = 30;
const TILESET_KEY = 'office-tiles';

// Renders one warroom's floor/walls/furniture from its static map JSON (frontend/public/maps/*.json).
// Agent sprites are out of scope here (Task 7) — map-loaded seat/spawn data is emitted on the
// EventBus so that later work can hook agent placement without this scene knowing about agents.
export class WarroomScene extends Phaser.Scene {
  constructor() {
    super('WarroomScene');
  }

  init(data) {
    this.mapName = data?.map || 'investment-room';
  }

  async create() {
    const basePath = process.env.PUBLIC_URL || '';
    const url = `${basePath}/maps/${this.mapName}.json`;
    let mapData;
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
      mapData = await res.json();
    } catch (err) {
      console.error(`[WarroomScene] failed to load map "${this.mapName}" from ${url}: ${err.message}`);
      return; // no map-loaded event — nothing rendered, but failure is visible instead of silent
    }

    const { spawnPoints, seatMap } = loadMapIntoScene(this, mapData, TILESET_KEY);

    this.cameras.main.setZoom(2);
    this.cameras.main.setBounds(0, 0, MAP_COLS * TILE_SIZE, MAP_ROWS * TILE_SIZE);

    EventBus.emit('map-loaded', { spawnPoints, seatMap });
  }
}
