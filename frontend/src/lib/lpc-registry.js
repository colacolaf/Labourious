// Loads and queries frontend/public/assets/lpc-registry.json (LPC "universal sprite sheet
// generator" style catalog: ~100 categories, each with items that map to spritesheet paths
// per bodyType, plus a `variants` color list and a `zPos` paint-order hint per layer).
//
// Registry shape (see frontend/public/assets/lpc-registry.json):
// {
//   bodyTypes: ["male", "female"],
//   categories: [
//     {
//       id: "body", type_name: "body", label: "Body", priority: 10,
//       items: [
//         {
//           key: "body", name: "Body Color", type: "body",
//           variants: ["light", "olive", ...],
//           layers: {
//             layer_1: { zPos: 10, paths: { male: "body/bodies/male", female: "body/bodies/female" } }
//           },
//           matchBodyColor: true, priority: 10
//         }, ...
//       ]
//     }, ...
//   ]
// }
//
// Spritesheet files on disk live at:
//   frontend/public/assets/lpc/spritesheets/{layer.paths[bodyType]}/walk/{variant}.png
// and each PNG is already a full 576x256 (9 cols x 4 rows x 64px) walk sheet.

const REGISTRY_URL = `${process.env.PUBLIC_URL || ''}/assets/lpc-registry.json`;
const SPRITE_BASE = `${process.env.PUBLIC_URL || ''}/assets/lpc/spritesheets`;

let registryPromise = null;

/** Fetches and caches the LPC registry JSON. Safe to call repeatedly; retries on failure. */
export function loadRegistry() {
  if (!registryPromise) {
    registryPromise = fetch(REGISTRY_URL)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to load LPC registry: ${res.status}`);
        }
        return res.json();
      })
      .catch((err) => {
        // Don't poison the cache with a permanently-rejected promise — clear it so the
        // next caller gets a fresh fetch attempt instead of a stuck failure for the page's life.
        registryPromise = null;
        throw err;
      });
  }
  return registryPromise;
}

export function getCategory(registry, categoryId) {
  return registry?.categories?.find((c) => c.id === categoryId) || null;
}

export function getCategoryIds(registry) {
  return (registry?.categories || []).map((c) => c.id);
}

export function getItem(registry, categoryId, itemKey) {
  const category = getCategory(registry, categoryId);
  return category?.items?.find((i) => i.key === itemKey) || null;
}

export function getItemVariants(item) {
  return item?.variants || [];
}

/**
 * Returns the paintable layer entries for one item + bodyType + variant, e.g.
 * [{ zPos, url }, ...]. Most items have a single `layer_1`; a few (capes, dresses)
 * define multiple internal layers, all painted with the same variant color.
 * ponytail: assumes one variant applies to every internal layer of an item — true for
 * everything used by the default appearances today; revisit if a multi-tone item shows up.
 */
export function getLayerPaintEntries(item, bodyType, variant) {
  if (!item?.layers) return [];
  return Object.keys(item.layers)
    .sort()
    .map((layerKey) => item.layers[layerKey])
    .filter((layer) => layer?.paths?.[bodyType])
    .map((layer) => ({
      zPos: layer.zPos ?? 0,
      url: `${SPRITE_BASE}/${layer.paths[bodyType]}/walk/${variant}.png`,
    }));
}
