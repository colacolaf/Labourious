import Phaser from 'phaser';
import { BootScene } from './scenes/BootScene';

export function createGame(parent) {
  return new Phaser.Game({
    type: Phaser.AUTO,
    parent,
    width: 1280,
    height: 960,
    pixelArt: true,
    backgroundColor: '#2d2d2d',
    scene: [BootScene],
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  });
}
