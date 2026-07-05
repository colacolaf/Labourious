import Phaser from 'phaser';
import { BootScene } from './scenes/BootScene';
import { WarroomScene } from './scenes/WarroomScene';

export function createGame(parent, map) {
  const game = new Phaser.Game({
    type: Phaser.AUTO,
    parent,
    width: 1280,
    height: 960,
    pixelArt: true,
    backgroundColor: '#2d2d2d',
    scene: [BootScene, WarroomScene],
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  });
  // Registry (not scene data) because BootScene is auto-started by the config array above
  // with no init data — this is the handoff point it reads from before starting WarroomScene.
  if (map) game.registry.set('map', map);
  return game;
}
