import Phaser from 'phaser';

// Pub/sub bridge between Phaser scenes and React components.
// Reuses Phaser's built-in EventEmitter rather than a custom implementation.
// Known events: 'scene-ready', 'spritesheet-ready', 'agent-clicked', 'map-loaded'.
// Single shared bus — assumes only one WarroomPhaserGame instance is mounted at a time. Scope per-instance if that changes.
export const EventBus = new Phaser.Events.EventEmitter();
