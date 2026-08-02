// ---------------------------------------------------------------------------
// agent-compositor.js — shared LPC character compositor.
//
// Port of deskrpg's src/lib/sprite-compositor.ts (compositeCharacter +
// getLayerPaths) plus the standstill-frame rule from GameScene.ts:
//   idleFrame = direction * SPRITE_COLS   (frame 0 of a row = idle;
//   walk sheet rows: 0=up/back, 1=left, 2=down/front, 3=right)
//
// Consumption: pass an agent's `layers` array (from assets/agents/agents.json,
// already zPos-sorted) to compositeCharacter() to build the 576×256 walk
// sheet, then drawStandstill() to crop the idle frame onto a preview canvas,
// centered by its non-transparent bounding box.
// ---------------------------------------------------------------------------

export const FRAME_WIDTH  = 64;
export const FRAME_HEIGHT = 64;
export const WALK_COLS    = 9;
export const WALK_SHEET_W = 576; // 9 * 64
export const WALK_SHEET_H = 256; // 4 * 64

// Walk-sheet row per direction (deskrpg: GameScene DIR_* + CharacterPreview).
export const DIR_ROW = { up: 0, left: 1, down: 2, right: 3 };

export function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Failed to load image: " + src));
    img.src = src;
  });
}

/**
 * Composite every layer of an appearance onto `canvas` (resized to 576×256).
 * Layers: [{ src, zPos }]. Drawn bottom-up by zPos — same semantics as
 * deskrpg's getLayerPaths() sort. Failed layers warn instead of throwing.
 */
export async function compositeCharacter(canvas, layers) {
  const sorted = [...layers].sort((a, b) => a.zPos - b.zPos);
  canvas.width  = WALK_SHEET_W;
  canvas.height = WALK_SHEET_H;

  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, WALK_SHEET_W, WALK_SHEET_H);
  ctx.imageSmoothingEnabled = false;

  const results = await Promise.allSettled(sorted.map((l) => loadImage(l.src)));
  for (const result of results) {
    if (result.status === "fulfilled") {
      ctx.drawImage(result.value, 0, 0, WALK_SHEET_W, WALK_SHEET_H);
    } else {
      console.warn("[agent-compositor] layer failed:", result.reason?.message);
    }
  }
}

// Bounding box of the non-transparent pixels in a region — LPC frames have
// empty margins, so this lets us center the figure in the preview canvas.
function getContentBox(ctx, x, y, w, h) {
  const data = ctx.getImageData(x, y, w, h).data;
  let minX = w, minY = h, maxX = -1, maxY = -1;
  for (let py = 0; py < h; py++) {
    for (let px = 0; px < w; px++) {
      if (data[(py * w + px) * 4 + 3] > 0) {
        if (px < minX) minX = px;
        if (px > maxX) maxX = px;
        if (py < minY) minY = py;
        if (py > maxY) maxY = py;
      }
    }
  }
  return { minX, minY, maxX, maxY };
}

/**
 * Crop the standstill frame (frame 0 of `direction`'s row) from a composited
 * sheet and blit it scaled + content-centered onto the preview canvas.
 */
export function drawStandstill(
  preview,
  sheet,
  { direction = "down", scale = 8, background = "#ffffff" } = {},
) {
  const row = DIR_ROW[direction] ?? DIR_ROW.down;
  const sx  = 0;
  const sy  = row * FRAME_HEIGHT;

  const sctx = sheet.getContext("2d");
  const box = getContentBox(sctx, sx, sy, FRAME_WIDTH, FRAME_HEIGHT);
  const bw = box.maxX - box.minX + 1;
  const bh = box.maxY - box.minY + 1;
  const ox = (preview.width - bw * scale) / 2 - box.minX * scale;
  const oy = (preview.height - bh * scale) / 2 - box.minY * scale;

  const pctx = preview.getContext("2d");
  pctx.fillStyle = background;
  pctx.fillRect(0, 0, preview.width, preview.height);
  pctx.imageSmoothingEnabled = false;
  pctx.drawImage(
    sheet,
    sx, sy, FRAME_WIDTH, FRAME_HEIGHT,
    ox, oy, FRAME_WIDTH * scale, FRAME_HEIGHT * scale,
  );
}
