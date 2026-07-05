// Sector Trading Office (swing_trading) theme colors — Task 5 of the Phase 11 DeskRPG
// redesign (docs/superpowers/specs/2026-07-04-deskrpg-redesign-design.md, Room 2).
// White analyst floor: bright, not the old red/black Pit.
//
// Shape matches map-loader.js's PALETTES table entries ({ floor, wall, door, carpet }, numeric
// hex colors for Phaser) so it plugs in as PALETTES.sector without further changes there.
export const SECTOR_PALETTE = {
  floor: 0xf5f5f5,
  wall: 0xffffff,
  door: 0xffffff,
  carpet: 0xeeeeee,
};

// Amber accent — whiteboard chart lines and ticker labels (drawSectorDecor in WarroomScene.js).
export const SECTOR_ACCENT = 0xd97706;
