import Phaser from 'phaser';
import { BootScene } from './scenes/BootScene';
import { WarroomScene } from './scenes/WarroomScene';

export function createGame(parent, map, room) {
  return new Phaser.Game({
    type: Phaser.AUTO,
    parent,
    width: 1280,
    height: 960,
    pixelArt: true,
    backgroundColor: '#2d2d2d',
    scene: [BootScene, WarroomScene],
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
    // preBoot runs synchronously inside Game.boot(), before any scene starts — the documented
    // hook for seeding the registry, vs. relying on BootScene.create() happening "later".
    callbacks: { preBoot: (game) => {
      if (map) game.registry.set('map', map);
      if (room) game.registry.set('room', room);
    } },
  });
}
