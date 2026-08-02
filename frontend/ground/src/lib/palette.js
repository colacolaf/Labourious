// palette.js
// ---------------------------------------------------------------------------
// Labourious Ground Floor Lobby — deskrpg-exact palette tokens.
//
// Source of truth: deskrpg's BootScene.ts + object-textures.ts. Every one of
// these hex values is used by deskrpg's runtime to draw the same 16 tile
// sprites and 11 object textures — keeping them identical guarantees the
// prototype is visually indistinguishable from an official deskrpg map.
//
// All values are decimal RGB integers in the 0xRRGGBB format expected by
// Phaser.GameObjects.Graphics.fillStyle().
// ---------------------------------------------------------------------------

export const COLORS = {
  // ── Floor / carpet (BootScene case 1 + case 12) ──
  floorBase:       0x8b8378, // warm gray carpet
  floorStroke:     0x7a7368,
  floorDot:        0x7f7a6e,

  carpetBase:      0x6b6560, // darker meeting-room carpet (tile 12)
  carpetStroke:    0x5e5a55,
  carpetDot:       0x625e58,

  // ── Walls (BootScene case 2) ──
  wallBase:        0x4a4a5e,
  wallHighlight:   0x6a6a7e,
  wallLine:        0x3a3a4e,
  wallEdge:        0x5a5a6e,

  // ── Door (BootScene case 7) ──
  doorFrame:       0x6b5a3a,
  doorPanel:       0x8b7a5a,
  doorPanelLine:   0x7a6a4a,
  doorHandle:      0xd4af37, // brass

  // ── Desk (BootScene case 3 / object-textures desk) ──
  deskTop:         0x6b4226,
  deskEdge:        0x523218,
  deskGrain:       0x7a5236,

  // ── Chair (BootScene case 4) ──
  chairSeat:       0x4060b0,
  chairBack:       0x3050a0,
  chairLeg:        0x333333,

  // ── Computer (BootScene case 5) ──
  computerMonitor: 0x222233,
  computerScreen:  0x1a3a2a,
  computerLed:     0x44ff44,
  computerStand:   0x444444,

  // ── Plant (BootScene case 6) ──
  plantPot:        0x8b4513,
  plantPotDark:    0x6b3210,
  plantLeaves:     0x2d8b2d,
  plantLeavesMid:  0x3aa53a,

  // ── Meeting table (BootScene case 8) ──
  meetingOuter:    0x4a3020,
  meetingHighlight:0x5a4030,
  meetingReflect:  0x6a5040,

  // ── Coffee (BootScene case 9) ──
  coffeeCounter:   0x5a4a3a,
  coffeeMachine:   0x333333,
  coffeeLed:       0xff3333,
  coffeeCup:       0xffffff,
  coffeeLiquid:    0x8b6914,

  // ── Water cooler (BootScene case 10) ──
  waterBase:       0xcccccc,
  waterBottle:     0x88bbff,
  waterLevel:      0x6699dd,
  waterCap:        0x4477bb,
  waterTap:        0x888888,

  // ── Bookshelf (BootScene case 11) ──
  bookshelfFrame:  0x5a3a1a,
  bookshelfShelf:  0x6b4a2a,
  bookshelfBooks: [0xcc3333, 0x3366cc, 0x33aa33, 0xccaa33, 0x9933cc, 0xcc6633],

  // ── Whiteboard (BootScene case 13) ──
  whiteboardFrame: 0xcccccc,
  whiteboard:      0xf0f0f0,
  whiteboardInk:   0x3366cc,
  whiteboardTray:  0xaaaaaa,

  // ── Reception desk (BootScene case 14) ──
  receptionBody:   0x8b6b3a,
  receptionTop:    0x9b7b4a,
  receptionPanel:  0x7b5b2a,
  receptionLogo:   0xd4af37,

  // ── Cubicle wall (BootScene case 15) ──
  cubicle:         0x888899,
  cubicleFrame:    0x777788,
  cubicleTexture:  0x9999aa,

  // ── Brass signage (added on top — deskrpg uses doorHandle gold elsewhere) ──
  brassText:       0xd4af37,
  brassShadow:     0x0b0b14,
};
