// ---------------------------------------------------------------------------
// scene.js — deskrpg-faithful small-office template loader.
//
// Canonical Phaser 3.90 Tiled flow:
//   1. preload():  synchronously register every tileset image + the Tiled
//                  JSON. Phaser's loader phase drains ALL queued loads
//                  before create() runs.
//   2. create():   parse the Tiled JSON via this.make.tilemap({key}),
//                  bind every tileset, create Layer + Objects in declared
//                  order via STRING layer names.
// ---------------------------------------------------------------------------

const TILED_JSON_URL = "/assets/templates/labourious-ground-floor.tiled.json";
const TILESET_DIR    = "assets/tilesets/builtin/";
const COLS = 28;  // matches the labourious template's grid width
const ROWS = 22;  // matches the labourious template's grid height

// Exact list of 42 tileset basenames referenced by /assets/templates/
// small-office.tiled.json (extracted from the file). Hard-coded so that
// preload() can register every image synchronously inside the loader phase.
const TILESET_FILES = [
  "small-office-tileset-ai.png",
  "소규모-오피스-맵.png",
  "stamp-4ff3e012-b8fc-4f37-b142-eb6211ac8855-edited.png",
  "stamp-85e84812-831a-4845-ae35-7e0ae078255a-edited.png",
  "stamp-a79638b2-6527-4792-81e4-6a97824fd156-edited.png",
  "stamp-52e50c59-fb9c-40e6-a0e5-3528619ab27b-edited.png",
  "stamp-54d175c9-f032-4a0e-9dc9-a7c67b200454-stamp-edited-foreground.png",
  "stamp-4788b8ca-a027-4673-9f60-593c89e3a1ae-stamp-edited-floor.png",
  "edited-selection-1774856337212.png",
  "nano-banana-pro_a-pixel-art-tileset-sprite-she_20260330_205454.png",
  "color-palette.png",
  "edited-selection-1774856447457.png",
  "stamp-c6cfeb00-99ea-4cde-9280-c32d8ebfc607-stamp-edited-paritition.png",
  "stamp-d08c026e-ef5c-4344-b066-80123f17a499-stamp-edited-floor.png",
  "stamp-2cf78e4e-e996-4b0d-9290-5b33df40d4c9-stamp-edited-paritition.png",
  "stamp-e9bf1410-0449-4cb9-9f71-6f6e40551402-edited.png",
  "edited-selection-1774857224660.png",
  "stamp-813f92d0-4977-41b5-98af-cd1a973057ce-edited.png",
  "stamp-e3a87a52-3ecf-48ea-ae24-bcebbfffbcdb-edited.png",
  "stamp-74d8d218-3535-4fec-bfda-6b6fb82ee0e7-edited.png",
  "stamp-efd330f8-c243-4508-9bed-20c074be8f08-edited.png",
  "stamp-d08c026e-ef5c-4344-b066-80123f17a499-stamp-edited-walls.png",
  "stamp-7ed500ec-5ee8-4ee1-906d-c926649b4d1f-stamp-edited-walls.png",
  "stamp-52e50c59-fb9c-40e6-a0e5-3528619ab27b-stamp-edited-foreground.png",
  "stamp-d08c026e-ef5c-4344-b066-80123f17a499-stamp-edited-foreground.png",
  "edited-selection-1774857575323.png",
  "stamp-5ac6ce84-4efd-497a-82d3-4b46a44f63d3-stamp-edited-floor.png",
  "edited-selection-1774858792925.png",
  "stamp-54d175c9-f032-4a0e-9dc9-a7c67b200454-stamp-edited-walls.png",
  "stamp-4ff3e012-b8fc-4f37-b142-eb6211ac8855-stamp-edited-walls.png",
  "stamp-4788b8ca-a027-4673-9f60-593c89e3a1ae-stamp-edited-paritition.png",
  "stamp-782212ef-4b96-4378-a705-afa87b4d3c2f-stamp-edited-floor.png",
  "stamp-efd330f8-c243-4508-9bed-20c074be8f08-stamp-edited-floor.png",
  "edited-selection-1774858252407.png",
  "stamp-db9a0ee8-6dbd-46e1-8425-efafd88bd054-edited.png",
  "stamp-7ed500ec-5ee8-4ee1-906d-c926649b4d1f-stamp-edited-floor.png",
  "stamp-ef2185bc-5680-4d2e-9abd-1da538c0a738-stamp-edited-floor.png",
  "edited-selection-1774856962259.png",
  "stamp-3f7a8f1e-c437-4527-8b37-42213b4b2e4a-edited.png",
  "nano-banana-pro_a-pixel-art-tileset-sprite-she_20260330_185733.png",
  "small-office-tileset-ai-back.png",
  "stamp-acaf4017-6515-4038-ad3e-86a9ceadc7af-edited.png",
];

class GroundLobbyScene extends Phaser.Scene {
  constructor() { super({ key: "GroundLobby" }); }

  // -------------------------------------------------------------------------
  // preload — synchronously register every tileset image and the Tiled JSON.
  // This runs inside Phaser's loader phase; once it completes, ALL queued
  // loads have finished and create() is invoked.
  // -------------------------------------------------------------------------
  preload() {
    // 1. Register every tileset PNG (URL-encode each path segment so Korean
    //    filenames + spaces fetch correctly over HTTP).
    for (const file of TILESET_FILES) {
      const key = `ts__${file}`;
      const url = TILESET_DIR + file.split("/").map(encodeURIComponent).join("/");
      this.load.image(key, url);
    }

    // 2. Register the Tiled JSON.
    this.load.tilemapTiledJSON("small-office", TILED_JSON_URL);
  }

  // -------------------------------------------------------------------------
  // create — the loader has finished. Build the tilemap + render.
  // -------------------------------------------------------------------------
  create() {
    const map = this.make.tilemap({ key: "small-office" });
    if (!map) {
      console.error("[small-office] make.tilemap returned null");
      return;
    }

    // Bind every tileset name → its registered image texture.
    // CRITICAL: addTilesetImage signature is
    //   (tilesetName, key, tileWidth, tileHeight, tileMargin, tileSpacing, gid)
    // CRITICAL PART 2: passing `ts.firstgid` as the 7th arg anchors Phaser's
    // gid-to-tileset resolution. Without it, when the JSON's `tilesets`
    // array isn't strictly firstgid-sorted, Phaser can resolve a gid against
    // the wrong tileset → wrong frame → partial furniture (chairs without
    // backs, monitors without screens).
    const tilesets = [];
    const cached = this.cache.tilemap.get("small-office");
    (cached.data.tilesets || []).forEach((ts) => {
      const fileName = (ts.image || "").split("/").pop();
      if (!fileName) return;
      const texKey = `ts__${fileName}`;
      const registered = map.addTilesetImage(
        ts.name,
        texKey,
        ts.tilewidth  || 32,
        ts.tileheight || 32,
        ts.margin     || 0,
        ts.spacing    || 0,
        ts.firstgid
      );
      if (registered) tilesets.push(registered);
    });
    console.log(`[small-office] tilesets bound: ${tilesets.length}`);

    // Render the visible tile layers in declared order, BY NAME (string).
    const layerRenderPlan = [
      { name: "Floor",      depth: 100 },
      { name: "Walls",      depth: 200 },
      { name: "Paritition", depth: 300 },
      { name: "Foreground", depth: 400 },
    ];
    for (const plan of layerRenderPlan) {
      const lyr = map.createLayer(plan.name, tilesets, 0, 0);
      if (lyr) lyr.setDepth(plan.depth);
      else console.warn(`[small-office] layer "${plan.name}" returned null`);
    }

    // Render the Objects objectgroup as individual sprites.
    const objectsLayer = (cached.data.layers || []).find(l => l.name === "Objects");
    if (objectsLayer && Array.isArray(objectsLayer.objects)) {
      const objGroupY = objectsLayer.y || 0;
      let spritesDrawn = 0;
      for (const o of objectsLayer.objects) {
        if (!o.gid) continue;
        const tileset = (cached.data.tilesets || []).find(
          ts => o.gid >= ts.firstgid && o.gid < ts.firstgid + (ts.tilecount || 1)
        );
        if (!tileset) continue;
        const fileName = (tileset.image || "").split("/").pop();
        if (!fileName) continue;
        const texKey = `ts__${fileName}`;
        if (!this.textures.exists(texKey)) continue;

        const frameIdx = o.gid - tileset.firstgid;
        const sprite = this.add.sprite(o.x, o.y + objGroupY, texKey, frameIdx);
        sprite.setOrigin(0, 1);
        sprite.setDepth(500 + (o.y + objGroupY));
        spritesDrawn++;
      }
      console.log(`[small-office] object sprites drawn: ${spritesDrawn}/${objectsLayer.objects.length}`);
    }
  }
}

// ---------------------------------------------------------------------------
// Signage — Press-Start-2P pixel labels matching deskrpg's editor UI chrome.
// Positioned next to the 4 side doors + the elevator + a centre plate.
// ---------------------------------------------------------------------------
function addSignage(scene) {
  const COL = COLS, ROW = ROWS;
  const typo = (size = 8, color = "#f4ebd0") => ({
    fontFamily: "'Press Start 2P', monospace",
    fontSize: size + "px",
    color,
    stroke: "#1a1a2e",
    strokeThickness: 2,
    align: "center",
  });

  // Centre floor plate.
  const plate = scene.add.text(
    (COL / 2) * 32, (ROW / 2) * 32 + 32,
    "· LOBBY ·", typo(10, "#2a3340")
  );
  plate.setOrigin(0.5, 0);
  plate.setDepth(2000);

  // 4 room-sign plaques floating above the doors on the 2 long sides.
  // Door rows are 8-9 (upper pair) and 14-15 (lower pair).
  const labels = [
    { text: "RESEARCH",   x: 1 * 32, y:  7 * 32 },
    { text: "SENTIMENT",  x: (COL - 1) * 32, y:  7 * 32 },
    { text: "ALT · DATA", x: 1 * 32, y: 13 * 32 },
    { text: "STORAGE",    x: (COL - 1) * 32, y: 13 * 32 },
  ];
  for (const L of labels) {
    const t = scene.add.text(L.x, L.y, L.text, typo(8, "#f4ebd0"));
    t.setOrigin(0.5, 0);
    t.setDepth(2000);
  }

  // Elevator plaque above the top centre (cols 13/15 + pier 14).
  const elev = scene.add.text(
    (COL / 2) * 32, 1 * 32,
    "G · FLOORS 2–4 · PENTHOUSE", typo(7, "#d4af37")
  );
  elev.setOrigin(0.5, 0);
  elev.setDepth(2000);

  // Reception plaque on the underside of the reception counter
  // (rows 4-5 / cols 12-15 → the brand label below the counter block).
  const brand = scene.add.text(
    (COL / 2) * 32, 7 * 32,
    "LABOURIOUS", typo(6, "#d4af37")
  );
  brand.setOrigin(0.5, 0);
  brand.setDepth(2000);
}

// ---------------------------------------------------------------------------
// Boot.
// ---------------------------------------------------------------------------
const config = {
  type: Phaser.AUTO,
  parent: "game-root",
  width: COLS * 32,   // 896
  height: ROWS * 32,  // 704
  backgroundColor: "#1a1a2e",
  pixelArt: true,
  scene: [GroundLobbyScene],
};

// Hook signage into the scene's create() flow.
const _origCreate = GroundLobbyScene.prototype.create;
GroundLobbyScene.prototype.create = function () {
  _origCreate.call(this);
  addSignage(this);
};

new Phaser.Game(config);
