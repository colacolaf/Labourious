import Phaser from 'phaser';
import { EventBus } from '../EventBus';

const TILESET_KEY = 'office-tiles';
const TILESET_PATH = `${process.env.PUBLIC_URL || ''}/assets/tilesets/office.png`;

export class BootScene extends Phaser.Scene {
  constructor() {
    super('BootScene');
  }

  preload() {
    // office.png doesn't exist yet (added in a later task) — don't let a 404 crash the boot.
    this.load.once('loaderror', (file) => {
      if (file.key === TILESET_KEY) {
        console.warn(`[BootScene] tileset not found at ${TILESET_PATH}, continuing without it`);
      }
    });
    this.load.image(TILESET_KEY, TILESET_PATH);

    // 1x1 transparent placeholder texture for agent sprites until real spritesheets are wired up.
    // '.' is Phaser's "transparent pixel" token in generated texture data.
    this.textures.generate('fallback-char', { data: ['.'], pixelWidth: 1, pixelHeight: 1 });
  }

  create() {
    EventBus.emit('scene-ready', this);
  }
}
