// ---------------------------------------------------------------------------
// build-agents.js — regenerates assets/agents/agents.json (+ layer PNGs) and
//                   the per-agent look.md docs from the deskrpg LPC registry.
//
// Usage:
//   node scripts/build-agents.js
//
// Required source (deskrpg clone — same repo the tiles were ported from):
//   /tmp/deskrpg/public/assets/lpc-registry.json
//   /tmp/deskrpg/public/assets/spritesheets/
// Override with env vars LPC_REGISTRY / LPC_SPRITESHEETS.
//
// To add agents for a new room: append entries to AGENTS below with
// `room`, `role`, `bodyType`, `look`, `desc` and an `items` map of
// { category: [itemKey, variant] }. Omit `hair` for shaved-bald characters.
//
// ROOM-STYLE RULE: unnamed agents should dress like the room's culture so the
// roster reads as one world — e.g. Quant = suits / Patagonia vests, Crypto =
// casual + gold chain, Sentiment = media/social/desk mix. Named agents carry
// the real person's researched look.
// ---------------------------------------------------------------------------

const fs = require("fs");
const path = require("path");

const LPC_REGISTRY    = process.env.LPC_REGISTRY    || "/tmp/deskrpg/public/assets/lpc-registry.json";
const LPC_SPRITESHEETS = process.env.LPC_SPRITESHEETS || "/tmp/deskrpg/public/assets/spritesheets";

const GROUND = path.resolve(__dirname, "..");                    // frontend/ground
const DST    = path.join(GROUND, "assets", "agents");
const DOCS   = path.resolve(__dirname, "..", "..", "..", "docs", "frontend"); // labourious/docs/frontend

// ---------------------------------------------------------------------------
// Agent specs. 6 example walkers (room 'examples') + 7 Research room agents.
// `docDir` is the docs folder relative to docs/frontend (research only).
// ---------------------------------------------------------------------------
const AGENTS = [
  // ── Examples ─────────────────────────────────────────────────────────────
  { id: "walkable-example", name: "Walkable Example Agent", room: "examples", role: "Example", bodyType: "male", look: "light skin · blue eyes · chestnut hair · blue tee · charcoal pants · brown boots",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_bangsshort", "chestnut"], clothes: ["torso_clothes_tshirt", "blue"], legs: ["legs_pants", "charcoal"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "female-default", name: "Female Default", room: "examples", role: "Example", bodyType: "female", look: "light skin · blue eyes · blonde bob · white blouse · navy skirt · brown boots",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_bob", "blonde"], clothes: ["torso_clothes_blouse", "white"], legs: ["legs_skirts_plain", "navy"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "formal-walker", name: "Formal Walker", room: "examples", role: "Example", bodyType: "male", look: "olive skin · brown eyes · black hair · white buttoned shirt · charcoal suit pants · black boots",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_bangs", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "scoop-walker", name: "Scoop Tee Walker", room: "examples", role: "Example", bodyType: "female", look: "bronze skin · green eyes · raven hair · pink scoop tee · charcoal leggings · brown boots",
    items: { body: ["body", "bronze"], eye_color: ["eye_color", "green"], hair: ["hair_bangslong", "raven"], clothes: ["torso_clothes_tshirt_scoop", "pink"], legs: ["legs_leggings", "charcoal"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "polo-walker", name: "Polo Walker", room: "examples", role: "Example", bodyType: "male", look: "brown skin · brown eyes · black bedhead · navy polo · gray pants · brown boots",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], hair: ["hair_bedhead", "black"], clothes: ["torso_clothes_shortsleeve_polo", "navy"], legs: ["legs_pants2", "gray"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "longsleeve-walker", name: "Longsleeve Walker", room: "examples", role: "Example", bodyType: "female", look: "light skin · blue eyes · ginger bob · white long-sleeve blouse · charcoal skirt · black boots",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_bob_side_part", "ginger"], clothes: ["torso_clothes_blouse_longsleeve", "white"], legs: ["legs_skirt_straight", "charcoal"], shoes: ["feet_boots_basic", "black"] } },

  // ── Research (Room 1) — Ground Floor Intake ─────────────────────────────
  { id: "michael-burry", docDir: "ground/research/michael-burry", name: "Michael Burry", room: "research", role: "Lead Researcher", lead: true, bodyType: "male", look: "shaved bald · white trimmed beard · plain gray tee · black pants",
    desc: "Michael Burry's signature look: shaved bald head, gray-white trimmed beard, plain dark tee — the man who shorted the housing bubble.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], beard: ["beards_trimmed", "white"], clothes: ["torso_clothes_tshirt", "gray"], legs: ["legs_pants", "black"], shoes: ["feet_boots_basic", "black"] } }, // no hair → shaved bald
  { id: "john-hempton", docDir: "ground/research/sec-regulatory", name: "John Hempton", room: "research", role: "SEC / Regulatory", bodyType: "male", look: "wispy gray hair · clean-shaven · navy polo · gray pants",
    desc: "John Hempton's look: wispy gray-white messy hair, clean-shaven, relaxed smart-casual navy polo — the Aussie fraud-hunting short seller of Bronte Capital.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_messy2", "gray"], clothes: ["torso_clothes_shortsleeve_polo", "navy"], legs: ["legs_pants", "gray"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "web-research", docDir: "ground/research/web-research", name: "Web Research Agent", room: "research", role: "Web Research", bodyType: "male", look: "black afro · teal v-neck tee · blue jeans",
    desc: "Web Research Agent: young, sharp digital-native analyst with a black afro and a teal v-neck tee.",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], hair: ["hair_afro", "black"], clothes: ["torso_clothes_tshirt_vneck", "teal"], legs: ["legs_pants", "blue"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "filings-intern", docDir: "ground/research/hedge-fund-political-filings-intern", name: "Hedge Fund & Political Filings Intern", room: "research", role: "Intern", bodyType: "male", look: "messy chestnut hair · white dress shirt · charcoal suit pants",
    desc: "Hedge Fund & Political Filings Intern: fresh-faced and eager in a white dress shirt and charcoal suit pants.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_bedhead", "chestnut"], clothes: ["torso_clothes_longsleeve_formal", "white"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "academic-research", docDir: "ground/research/academic-research", name: "Academic Research Agent", room: "research", role: "Academic Research", bodyType: "male", look: "thin white hair · maroon cardigan · charcoal slacks",
    desc: "Academic Research Agent: distinguished professor with thin white hair and a maroon cardigan.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "green"], hair: ["hair_balding", "white"], clothes: ["torso_clothes_longsleeve2_cardigan", "maroon"], legs: ["legs_pants2", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "news-aggregation", docDir: "ground/research/news-aggregation", name: "News Aggregation Agent", room: "research", role: "News Aggregation", bodyType: "female", look: "strawberry pixie cut · sky scoop tee · navy pants",
    desc: "News Aggregation Agent: sleek newsroom editor with a strawberry pixie cut and a sky scoop tee.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "green"], hair: ["hair_pixie", "strawberry"], clothes: ["torso_clothes_tshirt_scoop", "sky"], legs: ["legs_pants2", "navy"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "data-scout", docDir: "ground/research/data-scout", name: "Data Scout Agent", room: "research", role: "Data Scout", bodyType: "male", look: "chestnut buzzcut · forest field shirt · tan pants",
    desc: "Data Scout Agent: rugged field investigator with a chestnut buzzcut and a forest-green field shirt.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_buzzcut", "chestnut"], clothes: ["torso_clothes_longsleeve2", "forest"], legs: ["legs_pants", "tan"], shoes: ["feet_boots_basic", "brown"] } },

  // ── Sentiment (Room 7) — Ground Floor Intake ────────────────────────────
  // Style: media/social/desk mix — institutional formality, newsroom polish,
  // and one streetwear grinder. Named agents carry the real person's look.
  { id: "cathie-wood", docDir: "ground/sentiment/cathie-wood", name: "Cathie Wood", room: "sentiment", role: "Lead Sentiment", lead: true, bodyType: "female", look: "platinum-blonde side-part bob · bright pink blazer · black suit pants",
    desc: "Cathie Wood's look: platinum-blonde side-parted bob and a bright pink blazer — ARK Invest's innovation queen in her signature bold color.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_bob_side_part", "blonde"], clothes: ["torso_clothes_longsleeve2_buttoned", "pink"], legs: ["legs_formal", "black"], shoes: ["feet_boots_basic", "black"] } },
  { id: "jon-najarian", docDir: "ground/sentiment/options-flow-dark-pool", name: "Jon Najarian", room: "sentiment", role: "Options Flow & Dark Pool", bodyType: "male", look: "shaved head · gray goatee · brown flat cap · white buttoned shirt · charcoal suit",
    desc: "Jon Najarian's look: shaved head under a signature brown flat cap, gray goatee, white buttoned shirt — the options trader who is 'not your typical Wall Street suit'. (LPC has no glasses item, so his usual reading glasses are omitted — the flat cap + goatee carry the look.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], beard: ["beards_trimmed", "gray"], hat: ["hat_cap_leather", "brown"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } }, // no hair → shaved head
  { id: "news-sentiment", docDir: "ground/sentiment/news-sentiment", name: "News Sentiment Agent", room: "sentiment", role: "News Sentiment", bodyType: "female", look: "raven ponytail · sky newsroom blouse · charcoal pants",
    desc: "News Sentiment Agent: media-desk journalist in a sky blouse with a sleek raven ponytail — reads the mood of the headlines.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "green"], hair: ["hair_ponytail", "raven"], clothes: ["torso_clothes_longsleeve2", "sky"], legs: ["legs_pants2", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "social-media-retail", docDir: "ground/sentiment/social-media-retail", name: "Social Media & Retail Agent", room: "sentiment", role: "Social Media & Retail", bodyType: "male", look: "hood up · black hoodie · white tee · blue jeans",
    desc: "Social Media & Retail Agent: streetwear-grinder energy — hood up, white tee, jeans — the one tracking the vibe of the timeline.",
    items: { body: ["body", "bronze"], eye_color: ["eye_color", "brown"], hair: ["hair_afro", "black"], hat: ["hat_hood_cloth", "hood_black"], clothes: ["torso_clothes_tshirt_vneck", "white"], legs: ["legs_pants", "blue"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "insider-institutional", docDir: "ground/sentiment/insider-institutional", name: "Insider & Institutional Agent", room: "sentiment", role: "Insider & Institutional", bodyType: "male", look: "side-parted black hair · dark navy suit · charcoal trousers",
    desc: "Insider & Institutional Agent: buttoned-up institutional desk in a dark navy suit — watches the 13Fs and Form 4s.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "navy"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "analyst-earnings-revision", docDir: "ground/sentiment/analyst-earnings-revision", name: "Analyst & Earnings Revision Agent", room: "sentiment", role: "Analyst & Earnings Revision", bodyType: "female", look: "chestnut bob · lavender buttoned blouse · navy trousers",
    desc: "Analyst & Earnings Revision Agent: business-casual analyst desk in a lavender blouse and navy trousers — tracking the estimate cuts and raises.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_bob", "chestnut"], clothes: ["torso_clothes_longsleeve2_buttoned", "lavender"], legs: ["legs_pants2", "navy"], shoes: ["feet_boots_basic", "brown"] } },

  // ── Alternative Data (Room 13) — Ground Floor Intake ─────────────────────
  // Style: field ops meets tech — rugged utility for the satellite/weather
  // crew, startup hoodie for the traffic watcher. Named agents carry the
  // real person's researched look.
  { id: "matthew-granade", docDir: "ground/alt-data/matthew-granade", name: "Matthew Granade", room: "altdata", role: "Lead Alt Data", lead: true, bodyType: "male", look: "short chestnut hair · blue button-down · charcoal suit",
    desc: "Matthew Granade's look: short chestnut hair and a sharp blue button-down — Point72's CIO and the architect of Bridgewater's research engine. (Based on general profile knowledge — public photos not verified.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_parted", "chestnut"], clothes: ["torso_clothes_longsleeve2_buttoned", "blue"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "james-crawford", docDir: "ground/alt-data/satellite-geospatial", name: "James Crawford", room: "altdata", role: "Satellite & Geospatial", bodyType: "male", look: "short chestnut hair · light-blue button-down · dark denim",
    desc: "James Crawford's look: short dark-brown hair, clean-shaven, light-blue button-down — the Orbital Insight founder who reads the Earth from space.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_messy1", "chestnut"], clothes: ["torso_clothes_longsleeve2_buttoned", "sky"], legs: ["legs_pants2", "charcoal"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "supply-chain", docDir: "ground/alt-data/supply-chain", name: "Supply Chain Agent", room: "altdata", role: "Supply Chain", bodyType: "male", look: "buzzcut · forest utility vest · tan cargo pants",
    desc: "Supply Chain Agent: field-ops utility vest and cargo pants — tracking bills of lading from the warehouse floor.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_buzzcut", "chestnut"], clothes: ["torso_clothes_sleeveless2", "forest"], legs: ["legs_pants", "tan"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "consumer-spending", docDir: "ground/alt-data/consumer-spending", name: "Consumer Spending Agent", room: "altdata", role: "Consumer Spending", bodyType: "female", look: "chestnut ponytail · slate cardigan · jeans",
    desc: "Consumer Spending Agent: comfy cardigan and jeans — reading the receipts, one transaction at a time.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "green"], hair: ["hair_ponytail", "chestnut"], clothes: ["torso_clothes_longsleeve2_cardigan", "slate"], legs: ["legs_pants2", "blue"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "weather-commodity", docDir: "ground/alt-data/weather-commodity", name: "Weather & Commodity Agent", room: "altdata", role: "Weather & Commodity", bodyType: "male", look: "sandy messy hair · red bandana · forest field shirt · tan pants",
    desc: "Weather & Commodity Agent: field-weather rugged with a red bandana — chasing the storms that move the markets.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_messy2", "sandy"], hat: ["hat_bandana", "bandana_red"], clothes: ["torso_clothes_longsleeve2", "forest"], legs: ["legs_pants", "tan"], shoes: ["feet_boots_basic", "black"] } },
  { id: "web-app-traffic", docDir: "ground/alt-data/web-app-traffic", name: "Web & App Traffic Agent", room: "altdata", role: "Web & App Traffic", bodyType: "male", look: "navy hood up · gray tee · jeans",
    desc: "Web & App Traffic Agent: startup hoodie energy — watching the clicks, sessions and dwell time.",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], hair: ["hair_messy1", "black"], hat: ["hat_hood_cloth", "navy"], clothes: ["torso_clothes_tshirt_vneck", "gray"], legs: ["legs_pants", "blue"], shoes: ["feet_boots_basic", "brown"] } },
];

// ---------------------------------------------------------------------------
// Resolution — same rules as deskrpg's getLayerPaths():
//   ${head}→adult, ${expression}→default, eye_color special-cased to eyes/default,
//   head layer auto-added at zPos 45 matching the body skin variant.
// ---------------------------------------------------------------------------
const reg = JSON.parse(fs.readFileSync(LPC_REGISTRY, "utf8"));
const cats = Array.isArray(reg) ? reg : (reg.categories || []);
const byKey = {};
for (const c of cats) for (const it of (c.items || [])) byKey[it.key] = it;

function walkPaths(itemKey, bodyType, variant) {
  const it = byKey[itemKey];
  if (!it) { console.log("  !! missing item:", itemKey); return []; }
  const out = [];
  for (const ld of Object.values(it.layers)) {
    let base = ld.paths[bodyType];
    if (!base) continue;
    base = base.replace(/\$\{head\}/g, "adult").replace(/\$\{expression\}/g, "default");
    if (itemKey === "eye_color") base = "eyes/default";
    out.push({ zPos: ld.zPos, file: `${base}/walk/${variant}.png`, itemKey, variant });
  }
  return out;
}

function build() {
  const manifest = [];
  let copied = 0, missing = [];

  for (const agent of AGENTS) {
    const layers = [];
    for (const [, [itemKey, variant]] of Object.entries(agent.items)) {
      for (const l of walkPaths(itemKey, agent.bodyType, variant)) layers.push(l);
    }
    const bodyVariant = agent.items.body[1];
    layers.push({ zPos: 45, file: `head/human/${agent.bodyType}/walk/${bodyVariant}.png`, itemKey: "head", variant: bodyVariant });
    layers.sort((a, b) => a.zPos - b.zPos);

    const dir = path.join(DST, agent.id);
    fs.mkdirSync(dir, { recursive: true });
    const manifestLayers = [];
    const seen = new Set();
    for (const l of layers) {
      const src = path.join(LPC_SPRITESHEETS, l.file);
      if (!fs.existsSync(src)) { missing.push(`${agent.id}: ${l.file}`); continue; }
      const leaf = path.basename(l.file);
      let name = `z${String(l.zPos).padStart(3, "0")}-${leaf}`;
      if (seen.has(name)) name = `z${String(l.zPos).padStart(3, "0")}-${l.itemKey}-${leaf}`;
      seen.add(name);
      fs.copyFileSync(src, path.join(dir, name));
      manifestLayers.push({ src: `/assets/agents/${agent.id}/${name}`, zPos: l.zPos });
      copied++;
    }
    manifest.push({
      id: agent.id, name: agent.name, room: agent.room, role: agent.role,
      lead: Boolean(agent.lead), bodyType: agent.bodyType, look: agent.look,
      layers: manifestLayers,
    });

    // Per-agent look.md (research rooms only — the doc convention).
    if (agent.docDir) {
      const hairL  = layers.find((l) => l.itemKey.startsWith("hair"));
      const beardL = layers.find((l) => l.itemKey.startsWith("beards"));
      const md = `# Look & Feel\n\n${agent.desc || agent.look}\n\n` +
        `- **Skin:** ${agent.items.body[1]} · **Eyes:** ${agent.items.eye_color[1]}\n` +
        `- **Hair:** ${hairL ? hairL.itemKey.replace("hair_", "") + " · " + hairL.variant : "none (shaved bald)"}\n` +
        `- **Beard:** ${beardL ? beardL.itemKey.replace("beards_", "") + " · " + beardL.variant : "none"}\n` +
        `- **Clothes:** ${agent.look}\n\n` +
        `LPC composite manifest id: \`${agent.id}\` → \`frontend/ground/assets/agents/agents.json\`\n`;
      const docDir = path.join(DOCS, agent.docDir);
      fs.mkdirSync(docDir, { recursive: true });
      fs.writeFileSync(path.join(docDir, "look.md"), md);
    }
  }

  // Fail loudly BEFORE writing — a missing layer must never silently ship
  // (it would drop a part of the character), and a broken manifest must
  // never land on disk.
  if (missing.length) {
    console.error("ABORT: missing LPC layer files:");
    for (const m of missing) console.error("  -", m);
    process.exit(1);
  }

  fs.writeFileSync(path.join(DST, "agents.json"), JSON.stringify(manifest, null, 2));
  console.log("copied files:", copied);
  console.log("missing:", missing.length ? missing : "none");
  console.log("manifest agents:", manifest.length);
  for (const a of manifest) console.log(" -", a.id, `(${a.room}${a.lead ? ", lead" : ""}, ${a.layers.length} layers)`);
}

build();
