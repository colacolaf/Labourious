import Phaser from 'phaser';
import { EventBus } from '../EventBus';
import { loadMapIntoScene, TILE_SIZE } from '../../lib/map-loader';
import { SECTOR_ACCENT } from './palettes/sector-palette';
import { CUBICLE_PALETTE, CUBICLE_ACCENT } from './palettes/cubicle-palette';

const MAP_COLS = 40;
const MAP_ROWS = 30;
const TILESET_KEY = 'office-tiles';
const SECTOR_TICKERS = ['XLF', 'XLE', 'XLK'];
const MONITOR_FLICKER_FRAMES = 40; // cubicle theme only — see drawCubicleDecor

// Renders one warroom's floor/walls/furniture from its static map JSON (frontend/public/maps/*.json).
// Agent sprites are out of scope here (Task 7) — map-loaded seat/spawn data is emitted on the
// EventBus so that later work can hook agent placement without this scene knowing about agents.
export class WarroomScene extends Phaser.Scene {
  constructor() {
    super('WarroomScene');
  }

  init(data) {
    this.mapName = data?.map || 'investment-room';
    this.frameCount = 0; // cubicle theme only — drives monitor_wall flicker in update()
    this.monitorGlows = [];
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
    if (this.roomTheme === 'cubicle') {
      this.drawCubicleDecor(mapData);
    }

    this.cameras.main.setZoom(2);
    this.cameras.main.setBounds(0, 0, MAP_COLS * TILE_SIZE, MAP_ROWS * TILE_SIZE);

    EventBus.emit('map-loaded', { spawnPoints, seatMap });
  }

  // Cubicle theme only: called every frame by Phaser. Only does work when a cubicle map
  // actually populated monitorGlows — investment/sector rooms never touch this branch.
  update() {
    if (this.roomTheme !== 'cubicle') return;
    if (this.monitorGlows.length === 0) return;
    this.frameCount += 1;
    if (this.frameCount % MONITOR_FLICKER_FRAMES !== 0) return;
    this.monitorFlickerOn = !this.monitorFlickerOn;
    const alpha = this.monitorFlickerOn ? 0.9 : 0.35;
    this.monitorGlows.forEach((gfx) => gfx.setAlpha(alpha));
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

  // Cubicle theme only: shrink cubicle_wall's full-tile rect (painted by map-loader.js) down to
  // "50% visual height" by painting over its top half with the carpet color, and add a blue
  // glow overlay on each monitor_wall tile that update() flickers every 40 frames.
  drawCubicleDecor(mapData) {
    const cubicleWalls = (mapData.objects || []).filter((o) => o.type === 'cubicle_wall');
    cubicleWalls.forEach((wallObj) => {
      const x = wallObj.col * TILE_SIZE;
      const y = wallObj.row * TILE_SIZE;
      const depth = wallObj.row + 0.5; // ponytail: fractional so this never ties row+1's real-object depth band

      const halfHeightCut = this.add.graphics().setDepth(depth);
      halfHeightCut.fillStyle(CUBICLE_PALETTE.carpet, 1);
      halfHeightCut.fillRect(x, y, TILE_SIZE, TILE_SIZE / 2);
    });

    const monitors = (mapData.objects || []).filter((o) => o.type === 'monitor_wall');
    monitors.forEach((monitor) => {
      const x = monitor.col * TILE_SIZE + TILE_SIZE / 2;
      const y = monitor.row * TILE_SIZE + TILE_SIZE / 2;
      const depth = monitor.row + 0.5; // ponytail: see cubicle_wall depth comment above

      const glow = this.add.graphics().setDepth(depth);
      glow.fillStyle(CUBICLE_ACCENT, 1);
      glow.fillRect(x - TILE_SIZE / 2 + 3, y - TILE_SIZE / 2 + 3, TILE_SIZE - 6, TILE_SIZE - 6);
      this.monitorGlows.push(glow);
    });
    this.monitorFlickerOn = true;
  }
}
