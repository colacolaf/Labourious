import Phaser from 'phaser';
import { EventBus } from '../EventBus';
import { loadMapIntoScene, TILE_SIZE } from '../../lib/map-loader';
import { SECTOR_ACCENT } from './palettes/sector-palette';

const MAP_COLS = 40;
const MAP_ROWS = 30;
const TILESET_KEY = 'office-tiles';
const SECTOR_TICKERS = ['XLF', 'XLE', 'XLK'];

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

    // roomTheme's source of truth is the map JSON's own `theme` field (MapData schema) rather
    // than a separate React prop — avoids threading the same string through two places.
    this.roomTheme = mapData.theme;
    if (this.roomTheme === 'sector') {
      this.drawSectorDecor(mapData);
    }

    this.cameras.main.setZoom(2);
    this.cameras.main.setBounds(0, 0, MAP_COLS * TILE_SIZE, MAP_ROWS * TILE_SIZE);

    EventBus.emit('map-loaded', { spawnPoints, seatMap });
  }

  // Sector theme only: hand-drawn whiteboard chart doodles + ticker labels, and paper-pile
  // decals on top of the paper_stack objects map-loader.js already painted as plain rects.
  drawSectorDecor(mapData) {
    const whiteboards = (mapData.objects || []).filter((o) => o.type === 'whiteboard');
    whiteboards.forEach((wb, i) => {
      const x = wb.col * TILE_SIZE + TILE_SIZE / 2;
      const y = wb.row * TILE_SIZE + TILE_SIZE / 2;
      const depth = wb.row + 0.5; // ponytail: fractional so this never ties row+1's real-object depth band

      const chart = this.add.graphics().setDepth(depth);
      chart.lineStyle(1, SECTOR_ACCENT, 1);
      chart.beginPath();
      chart.moveTo(x - 10, y + 4);
      chart.lineTo(x - 4, y - 4);
      chart.lineTo(x + 2, y + 1);
      chart.lineTo(x + 10, y - 6);
      chart.strokePath();

      this.add.text(x, y + 9, SECTOR_TICKERS[i] || '', {
        fontFamily: 'monospace',
        fontSize: '7px',
        color: '#d97706',
      }).setOrigin(0.5).setDepth(depth);
    });

    const paperStacks = (mapData.objects || []).filter((o) => o.type === 'paper_stack');
    paperStacks.forEach((ps) => {
      const x = ps.col * TILE_SIZE + TILE_SIZE / 2;
      const y = ps.row * TILE_SIZE + TILE_SIZE / 2;
      const decal = this.add.graphics().setDepth(ps.row + 0.5); // ponytail: see whiteboard depth comment above
      decal.fillStyle(0xd1d5db, 1);
      decal.fillRect(x - 9, y - 1, 18, 7);
      decal.fillStyle(0xe5e7eb, 1);
      decal.fillRect(x - 7, y - 6, 14, 6);
    });
  }
}
