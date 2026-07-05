// Composites a full LPC character walk-sheet (576x256, 9 cols x 4 rows x 64px frames) onto
// a canvas by layering LPC spritesheets in registry zPos order (body first, clothing/hair/
// accessories on top — zPos is the registry's own paint-order hint, see lpc-registry.js).
import { loadRegistry, getItem, getLayerPaintEntries } from './lpc-registry';

export const SHEET_WIDTH = 576;
export const SHEET_HEIGHT = 256;

// Per-canvas call-generation token so an in-flight compositeCharacter call whose images
// load slowly can't overwrite a canvas after a newer call for the same canvas has started.
const latestCallByCanvas = new WeakMap();

// CharacterAppearance shape:
// { bodyType: "male" | "female", layers: { [category]: { itemKey, variant } | null } }
const DEFAULT_BODY_LAYER = { itemKey: 'body', variant: 'light' };

/**
 * Fills in sane defaults for a partial/malformed appearance so compositeCharacter never
 * crashes: bodyType defaults to "male", and the "body" layer (the base skin — without it
 * the character is invisible) defaults to a plain light-skinned body. Every other category
 * is normalized to either a valid { itemKey, variant } pair or null (meaning "skip it").
 */
export function normalizeAppearance(appearance) {
  const bodyType = appearance?.bodyType === 'female' ? 'female' : 'male';
  const inputLayers = appearance?.layers || {};

  const layers = {};
  for (const [category, layer] of Object.entries(inputLayers)) {
    layers[category] = layer?.itemKey && layer?.variant ? layer : null;
  }
  if (!layers.body) {
    layers.body = DEFAULT_BODY_LAYER;
  }

  return { bodyType, layers };
}

function loadImage(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => {
      console.warn(`[sprite-compositor] failed to load layer image: ${url}`);
      resolve(null);
    };
    img.src = url;
  });
}

/** Draws the composited walk-sheet for `appearance` onto `canvas`. */
export async function compositeCharacter(canvas, appearance) {
  const callId = (latestCallByCanvas.get(canvas) || 0) + 1;
  latestCallByCanvas.set(canvas, callId);
  const isStale = () => latestCallByCanvas.get(canvas) !== callId;

  const registry = await loadRegistry();
  if (isStale()) return;
  const normalized = normalizeAppearance(appearance);

  const entries = [];
  for (const [categoryId, layer] of Object.entries(normalized.layers)) {
    if (!layer) continue;
    const item = getItem(registry, categoryId, layer.itemKey);
    if (!item) {
      console.warn(`[sprite-compositor] unknown LPC item ${categoryId}/${layer.itemKey}`);
      continue;
    }
    entries.push(...getLayerPaintEntries(item, normalized.bodyType, layer.variant));
  }
  entries.sort((a, b) => a.zPos - b.zPos);

  const images = await Promise.all(entries.map((entry) => loadImage(entry.url)));
  if (isStale()) return;

  canvas.width = SHEET_WIDTH;
  canvas.height = SHEET_HEIGHT;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, SHEET_WIDTH, SHEET_HEIGHT);
  for (const img of images) {
    if (isStale()) return;
    if (img) ctx.drawImage(img, 0, 0);
  }
}
