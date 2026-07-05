// Day Trading Floor (day_trading) theme colors — Task 6 of the Phase 11 DeskRPG
// redesign (docs/superpowers/specs/2026-07-04-deskrpg-redesign-design.md, Room 3).
// Cool gray cubicle farm, blue monitor accent — higher energy than investment, and
// explicitly not the old red/black Pit palette.
//
// Shape matches map-loader.js's PALETTES table entries ({ floor, wall, door, carpet }, numeric
// hex colors for Phaser) so it plugs in as PALETTES.cubicle without further changes there.
export const CUBICLE_PALETTE = {
  floor: 0x6b7280,
  wall: 0x9ca3af,
  door: 0x3b82f6,
  carpet: 0x5b6370,
};

// Blue accent — cubicle wall outline and monitor glow (drawCubicleDecor in WarroomScene.js).
export const CUBICLE_ACCENT = 0x3b82f6;
