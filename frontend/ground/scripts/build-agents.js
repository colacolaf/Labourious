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
// Extra item keys (e.g. `vest:`, `jacket:`) layer over `clothes:` by zPos —
// that's how the dress-shirt-under-fleece-vest quant uniform is built.
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

  // ── Quant (Room 4) — Floor 2 Analysis ─────────────────────────────────────
  // Style: strictly professional + the analyst uniform — dress shirt under a
  // Patagonia-style fleece vest (the Wall Street stereotype), blazers for the
  // partners. Named agents carry the real person's researched look.
  { id: "jim-simons", docDir: "floor-2/quant/jim-simons", name: "Jim Simons", room: "quant", role: "Lead Quant", lead: true, bodyType: "male", look: "white balding hair · open white shirt · navy blazer · charcoal slacks",
    desc: "Jim Simons' look: thin white hair, classic glasses, open-collar white shirt under a navy blazer — the Renaissance founder who famously never wore socks. (LPC has no glasses item, so his glasses are omitted.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_balding", "white"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "navy"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "ed-thorp", docDir: "floor-2/quant/statistical-arbitrage", name: "Ed Thorp", room: "quant", role: "Statistical Arbitrage", bodyType: "male", look: "black side-parted hair · white button-down · maroon sweater vest · gray slacks",
    desc: "Ed Thorp's look: neat dark side-parted hair, clean-shaven, horn-rimmed glasses and a knit sweater vest over a crisp button-down — the MIT professor who beat the dealer, then the market. (LPC has no glasses item, so his horn-rims are omitted.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], vest: ["torso_clothes_vest", "maroon"], legs: ["legs_formal", "gray"], shoes: ["feet_boots_basic", "black"] } },
  { id: "factor-analysis", docDir: "floor-2/quant/factor-analysis", name: "Factor Analysis Agent", room: "quant", role: "Factor Analysis", bodyType: "male", look: "black hair · white button-down · navy Patagonia vest · charcoal slacks",
    desc: "Factor Analysis Agent: the analyst uniform itself — crisp white button-down under a navy Patagonia-style fleece vest with charcoal slacks.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], vest: ["torso_clothes_vest", "navy"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "options-volatility", docDir: "floor-2/quant/options-volatility", name: "Options & Volatility Agent", room: "quant", role: "Options & Volatility", bodyType: "male", look: "gray side-parted hair · sky button-down · forest green vest · gray slacks",
    desc: "Options & Volatility Agent: senior desk hand in a forest-green vest over a sky button-down — speaks fluent vega.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_parted", "gray"], clothes: ["torso_clothes_longsleeve2_buttoned", "sky"], vest: ["torso_clothes_vest", "forest"], legs: ["legs_pants2", "gray"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "momentum-trend", docDir: "floor-2/quant/momentum-trend", name: "Momentum & Trend Agent", room: "quant", role: "Momentum & Trend", bodyType: "female", look: "chestnut ponytail · lavender button-down · black vest · navy slacks",
    desc: "Momentum & Trend Agent: trend-chasing desk analyst in a black vest over a lavender button-down.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "green"], hair: ["hair_ponytail", "chestnut"], clothes: ["torso_clothes_longsleeve2_buttoned", "lavender"], vest: ["torso_clothes_vest", "black"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "machine-learning", docDir: "floor-2/quant/machine-learning", name: "Machine Learning Agent", room: "quant", role: "Machine Learning", bodyType: "male", look: "black buzzcut · white shirt · black suit jacket · black slacks",
    desc: "Machine Learning Agent: the serious one in a full black suit — trains the models that train on the markets.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_buzzcut", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "black"], legs: ["legs_formal", "black"], shoes: ["feet_boots_basic", "black"] } },
  { id: "regime-detection", docDir: "floor-2/quant/regime-detection", name: "Regime Detection Agent", room: "quant", role: "Regime Detection", bodyType: "female", look: "gray bob · white button-down · charcoal vest · navy slacks",
    desc: "Regime Detection Agent: watches the macro switches — salt-and-pepper bob, charcoal vest over a white button-down.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_bob_side_part", "gray"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], vest: ["torso_clothes_vest", "charcoal"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "risk-budgeting-allocation", docDir: "floor-2/quant/risk-budgeting-allocation", name: "Risk Budgeting & Allocation Agent", room: "quant", role: "Risk Budgeting & Allocation", bodyType: "female", look: "raven braid · slate button-down · tan vest · charcoal slacks",
    desc: "Risk Budgeting & Allocation Agent: keeper of the capital — slate button-down and a tan vest, pencil down when the allocations move.",
    items: { body: ["body", "bronze"], eye_color: ["eye_color", "brown"], hair: ["hair_braid", "raven"], clothes: ["torso_clothes_longsleeve2_buttoned", "slate"], vest: ["torso_clothes_vest", "tan"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "brown"] } },

  // ── Security — Perimeter (main door) + Penthouse (PM bodyguard) ───────────
  // Style: BIG + BROAD. LPC bodies are one size, so bulk comes from heavy dark
  // layering — full beards, buzzcuts/shaved heads, tactical vest (armour_leather)
  // and suit-jacket + tie + chain stacks that widen the silhouette.
  { id: "entrance-bodyguard", docDir: "ground/perimeter/entrance-bodyguard", name: "Entrance Bodyguard Agent", room: "perimeter", role: "Main Door", bodyType: "male", look: "buzzcut · full black beard · black tactical shirt + vest · black slacks",
    desc: "Entrance Bodyguard: the first line at the main door — a big, broad wall of a man in a black tactical vest over a black shirt, full beard, buzzcut. Vets every request before it reaches the building.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_buzzcut", "black"], beard: ["beards_medium", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "black"], vest: ["torso_armour_leather", "black"], legs: ["legs_formal", "black"], shoes: ["feet_boots_basic", "black"] } },
  { id: "pm-bodyguard", docDir: "penthouse/agents/pm-bodyguard", name: "PM Bodyguard", room: "penthouse", role: "Last Line of Defense", bodyType: "male", look: "shaved head · trimmed beard · black suit + tie · gold chain · earpiece",
    desc: "PM Bodyguard: stands by the penthouse window in a black suit with a tie, gold chain and a comms earpiece — loyal, protective, silent until the PM is about to make a catastrophic call. (LPC has no watch item, so the wristwatch is omitted — the gold chain + earpiece stud carry the accessories.)",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], beard: ["beards_trimmed", "black"], chain: ["neck_necklace_chain", "gold"], ear: ["facial_earrings_stud", "silver"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "black"], tie: ["neck_necktie", "black"], legs: ["legs_formal", "black"], shoes: ["feet_boots_basic", "black"] } }, // no hair → shaved head

  // ── Crypto (Room 14) — Floor 2 Digital Frontier ───────────────────────────
  // Style: the crypto stereotype — hoodies (up for the degens), gold chains,
  // t-shirts, jeans, sneakers. Zero formality. Named agents carry the real
  // person's researched look.
  { id: "vitalik-buterin", docDir: "floor-2/crypto/vitalik-buterin", name: "Vitalik Buterin", room: "crypto", role: "Lead Crypto", lead: true, bodyType: "male", look: "long messy brown hair · light stubble · gray hoodie · blue jeans · white sneakers",
    desc: "Vitalik Buterin's look: the iconic mop of long wavy brown hair, a few days of scruff, and the gray hoodie + jeans + sneakers of the Ethereum co-founder who codes through conferences.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_long_messy", "chestnut"], beard: ["beards_5oclock_shadow", "chestnut"], clothes: ["torso_clothes_longsleeve2", "gray"], legs: ["legs_pants", "blue"], shoes: ["feet_shoes_basic", "white"] } },
  { id: "alex-svanevik", docDir: "floor-2/crypto/on-chain-analytics", name: "Alex Svanevik", room: "crypto", role: "On-Chain Analytics", bodyType: "male", look: "sandy short hair · light stubble · navy hoodie · charcoal pants · black sneakers",
    desc: "Alex Svanevik's look: short sandy-blonde crop, light stubble, navy hoodie — the Nansen CEO who reads the blockchain in Singapore smart-casual.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_curly_short", "sandy"], beard: ["beards_5oclock_shadow", "sandy"], clothes: ["torso_clothes_longsleeve2", "navy"], legs: ["legs_pants2", "charcoal"], shoes: ["feet_shoes_basic", "black"] } },
  { id: "defi-yield", docDir: "floor-2/crypto/defi-yield", name: "DeFi & Yield Agent", room: "crypto", role: "DeFi & Yield", bodyType: "male", look: "black hoodie up · gold chain · blue jeans · white sneakers",
    desc: "DeFi & Yield Agent: hood up, gold chain out, jeans — the degen chasing the next basis point on the yield curve of a new pool.",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], hair: ["hair_messy1", "black"], hat: ["hat_hood_cloth", "black"], chain: ["neck_necklace_chain", "gold"], clothes: ["torso_clothes_longsleeve2", "black"], legs: ["legs_pants", "blue"], shoes: ["feet_shoes_basic", "white"] } },
  { id: "tokenomics", docDir: "floor-2/crypto/tokenomics", name: "Tokenomics Agent", room: "crypto", role: "Tokenomics", bodyType: "female", look: "raven ponytail · white v-neck tee · gold chain · black pants · white sneakers",
    desc: "Tokenomics Agent: designs supply schedules and unlock curves — white tee, gold chain, sneakers.",
    items: { body: ["body", "bronze"], eye_color: ["eye_color", "brown"], hair: ["hair_ponytail", "raven"], chain: ["neck_necklace_chain", "gold"], clothes: ["torso_clothes_tshirt_vneck", "white"], legs: ["legs_pants2", "black"], shoes: ["feet_shoes_basic", "white"] } },
  { id: "protocol-risk", docDir: "floor-2/crypto/protocol-risk", name: "Protocol Risk Agent", room: "crypto", role: "Protocol Risk", bodyType: "male", look: "black hair · black flat cap · charcoal tee · silver chain · gray pants",
    desc: "Protocol Risk Agent: audits the smart contracts before the exploit does — black flat cap, charcoal tee, silver chain.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_messy2", "black"], hat: ["hat_cap_leather", "black"], chain: ["neck_necklace_chain", "silver"], clothes: ["torso_clothes_tshirt_vneck", "charcoal"], legs: ["legs_pants", "gray"], shoes: ["feet_shoes_basic", "black"] } },

  // ── Fundamental (Room 5) — Floor 2 Company Analysis ──────────────────────
  // Style: the old-school value-investor uniform — navy/charcoal/gray suits,
  // white shirts, ties (one bowtie, one suspenders-and-sleeves look). Named
  // agents carry the real person's researched look.
  { id: "warren-buffett", docDir: "floor-2/fundamental/warren-buffett", name: "Warren Buffett", room: "fundamental", role: "Lead Fundamental", lead: true, bodyType: "male", look: "white hair · navy suit · white shirt · red tie",
    desc: "Warren Buffett's look: snow-white hair, thick tortoiseshell glasses, and a navy suit with a red tie — the Oracle of Omaha, sipping a Cherry Coke between value picks. (LPC has no glasses item, so his iconic glasses are omitted.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_parted", "white"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "navy"], tie: ["neck_necktie", "red"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "harry-markopolos", docDir: "floor-2/fundamental/forensic-accounting", name: "Harry Markopolos", room: "fundamental", role: "Forensic Accounting", bodyType: "male", look: "short dark hair · light-gray suit · white shirt · navy tie",
    desc: "Harry Markopolos's look: neat dark hair, thin metal-frame glasses and his famous light-gray suit — the forensic accountant who chased Madoff for nine years before the world listened. (LPC has no glasses item, so his glasses are omitted.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "gray"], tie: ["neck_necktie", "navy"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "dcf-valuation", docDir: "floor-2/fundamental/dcf-valuation", name: "DCF & Valuation Agent", room: "fundamental", role: "DCF & Valuation", bodyType: "male", look: "chestnut hair · navy suit · white shirt · blue tie",
    desc: "DCF & Valuation Agent: the discount-rate desk — navy suit, blue tie, terminal value on the brain.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "chestnut"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "navy"], tie: ["neck_necktie", "blue"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "moat-competitive-analysis", docDir: "floor-2/fundamental/moat-competitive-analysis", name: "Moat & Competitive Analysis Agent", room: "fundamental", role: "Moat & Competitive Analysis", bodyType: "male", look: "gray hair · charcoal suit · white shirt · maroon tie",
    desc: "Moat & Competitive Analysis Agent: the Porter's-five-forces desk — charcoal suit, maroon tie, measuring the moats.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_parted", "gray"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "charcoal"], tie: ["neck_necktie", "maroon"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "management-quality", docDir: "floor-2/fundamental/management-quality", name: "Management Quality Agent", room: "fundamental", role: "Management Quality", bodyType: "male", look: "black hair · navy suit · sky shirt · black bowtie",
    desc: "Management Quality Agent: the people-reader — navy suit, sky shirt and a black bowtie while he sizes up the CEO.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_messy1", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "sky"], jacket: ["torso_jacket_collared", "navy"], tie: ["neck_bowtie", "black"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "catalyst-event", docDir: "floor-2/fundamental/catalyst-event", name: "Catalyst & Event Agent", room: "fundamental", role: "Catalyst & Event", bodyType: "male", look: "black bedhead hair · charcoal suit · open white shirt",
    desc: "Catalyst & Event Agent: the youngest on the floor — charcoal suit, open collar, watching for the trigger event.",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], hair: ["hair_bedhead", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "charcoal"], legs: ["legs_formal", "gray"], shoes: ["feet_boots_basic", "brown"] } }, // no tie → open collar
  { id: "industry-structure", docDir: "floor-2/fundamental/industry-structure", name: "Industry Structure Agent", room: "fundamental", role: "Industry Structure", bodyType: "male", look: "balding gray hair · white shirt · navy suspenders · navy tie",
    desc: "Industry Structure Agent: the old-school analyst with sleeves rolled up — white shirt, navy suspenders, tie; no jacket needed when you've seen every cycle since the 80s.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "green"], hair: ["hair_balding", "gray"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], suspenders: ["torso_aprons_suspenders", "navy"], tie: ["neck_necktie", "navy"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },

  // ── Macro (Room 3) — Floor 2 Global Stage ────────────────────────────────
  // Style: the global-macro desk — sober central-bank suits, one bond-desk
  // woman, TV-guest polish. Everyone distinct: no two share hair + shirt +
  // tie. Named agents carry the real person's researched look.
  { id: "larry-fink", docDir: "floor-2/macro/larry-fink", name: "Larry Fink", room: "macro", role: "Lead Macro", lead: true, bodyType: "male", look: "silver hair · navy suit · open blue shirt",
    desc: "Larry Fink's look: thinning silver hair, thin-framed executive glasses, and the signature navy suit with an open-collar blue shirt and no tie — the BlackRock CEO's boardroom-casual uniform. (LPC has no glasses item, so his glasses are omitted.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "white"], clothes: ["torso_clothes_longsleeve2_buttoned", "blue"], jacket: ["torso_jacket_collared", "navy"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } }, // no tie → open collar
  { id: "ian-bremmer", docDir: "floor-2/macro/geopolitical-risk", name: "Ian Bremmer", room: "macro", role: "Geopolitical Risk", bodyType: "male", look: "gray hair · charcoal suit · sky shirt · navy tie",
    desc: "Ian Bremmer's look: short gray hair, thick bold glasses and a sharp dark suit on every geopolitical panel — the Eurasia Group founder who reads the world's crises for a living. (LPC has no glasses item, so his thick frames are omitted.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "gray"], clothes: ["torso_clothes_longsleeve2_buttoned", "sky"], jacket: ["torso_jacket_collared", "charcoal"], tie: ["neck_necktie", "navy"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "central-bank-liquidity", docDir: "floor-2/macro/central-bank-liquidity", name: "Central Bank & Liquidity Agent", room: "macro", role: "Central Bank & Liquidity", bodyType: "male", look: "balding gray hair · navy suit · white shirt · black tie",
    desc: "Central Bank & Liquidity Agent: the sober central-banking type — balding gray hair, navy suit, black tie, watching the balance sheets drain.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_balding", "gray"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "navy"], tie: ["neck_necktie", "black"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "currency-sovereign-debt", docDir: "floor-2/macro/currency-sovereign-debt", name: "Currency & Sovereign Debt Agent", room: "macro", role: "Currency & Sovereign Debt", bodyType: "female", look: "chestnut bob · charcoal suit · white shirt · gray tie",
    desc: "Currency & Sovereign Debt Agent: the bond-desk analyst in a charcoal suit with a gray tie — tracking the reserves, the spreads, and the defaults before they print.",
    items: { body: ["body", "bronze"], eye_color: ["eye_color", "brown"], hair: ["hair_bob", "chestnut"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "charcoal"], tie: ["neck_necktie", "gray"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "global-growth-tracker", docDir: "floor-2/macro/global-growth-tracker", name: "Global Growth Tracker Agent", room: "macro", role: "Global Growth Tracker", bodyType: "male", look: "black hair · navy suit · lavender shirt · green tie",
    desc: "Global Growth Tracker Agent: the PMI desk — navy suit, lavender shirt, green tie, refreshing the composite indices every single morning.",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], hair: ["hair_messy1", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "lavender"], jacket: ["torso_jacket_collared", "navy"], tie: ["neck_necktie", "green"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "brown"] } },

  // ── Technical (Room 6) — Floor 2 Price Action ────────────────────────────
  // Style: the chart room — one blazer-and-beard lead, then startup-casual:
  // hoodies, polos, tees, sneakers. Everyone distinct: no shared hair+shirt
  // combo, one beard in the room (Minervini's).
  { id: "mark-minervini", docDir: "floor-2/technical/mark-minervini", name: "Mark Minervini", room: "technical", role: "Lead Technical", lead: true, bodyType: "male", look: "shaved bald · gray trimmed beard · navy blazer · open white shirt",
    desc: "Mark Minervini's look: shaved bald head, neatly trimmed gray beard and a navy blazer over an open-collar white shirt — the US Investing Champion, tie-less on CNBC.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], beard: ["beards_trimmed", "gray"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "navy"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } }, // no hair → shaved bald
  { id: "technical-signal-engine", docDir: "floor-2/technical/technical-signal-engine", name: "Technical Signal Engine Agent", room: "technical", role: "Technical Signal Engine", bodyType: "male", look: "black hair · charcoal hoodie · blue jeans · white sneakers",
    desc: "Technical Signal Engine Agent: the overnight coder — charcoal hoodie, jeans, sneakers, and a triple screen setup of moving averages.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_messy1", "black"], clothes: ["torso_clothes_longsleeve2", "charcoal"], legs: ["legs_pants", "blue"], shoes: ["feet_shoes_basic", "white"] } },
  { id: "volume-order-flow", docDir: "floor-2/technical/volume-order-flow", name: "Volume & Order Flow Agent", room: "technical", role: "Volume & Order Flow", bodyType: "male", look: "chestnut hair · blue polo · charcoal pants",
    desc: "Volume & Order Flow Agent: the tape reader — blue polo, watching the footprint charts fill in one candle at a time.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "green"], hair: ["hair_buzzcut", "chestnut"], clothes: ["torso_clothes_shortsleeve_polo", "blue"], legs: ["legs_pants2", "charcoal"], shoes: ["feet_shoes_basic", "black"] } },
  { id: "chart-pattern", docDir: "floor-2/technical/chart-pattern", name: "Chart & Pattern Agent", room: "technical", role: "Chart & Pattern", bodyType: "male", look: "balding gray hair · sky polo · charcoal pants",
    desc: "Chart & Pattern Agent: the classic chartist — balding gray hair, sky polo, glasses on the desk reading double tops and head-and-shoulders. (LPC has no glasses item, so his reading glasses are omitted.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_balding", "gray"], clothes: ["torso_clothes_shortsleeve_polo", "sky"], legs: ["legs_pants2", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "market-microstructure", docDir: "floor-2/technical/market-microstructure", name: "Market Microstructure Agent", room: "technical", role: "Market Microstructure", bodyType: "female", look: "black bob · charcoal v-neck tee · blue jeans · white sneakers",
    desc: "Market Microstructure Agent: the startup quant — black bob, charcoal v-neck, jeans and sneakers while she models the order book tick by tick.",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], hair: ["hair_bob", "black"], clothes: ["torso_clothes_tshirt_vneck", "charcoal"], legs: ["legs_pants", "blue"], shoes: ["feet_shoes_basic", "white"] } },

  // ── Risk (Room 2) — Floor 3 Judgment ─────────────────────────────────────
  // Style: Reddit-researched risk-room stereotypes — the rumpled middle-office
  // modeler, the tweed-blazer correlation professor, the fleece-vest drawdown
  // monitor, the sweater-vest factor quant. Named agents carry the real
  // person's researched look.
  { id: "nassim-taleb", docDir: "floor-3/risk/nassim-taleb", name: "Nassim Taleb", room: "risk", role: "Lead Risk", lead: true, bodyType: "male", look: "salt-pepper hair · gray full beard · black turtleneck · black slacks",
    desc: "Nassim Taleb's look: salt-and-pepper hair, a full trimmed beard and the famous black turtleneck — the Black Swan author, olive-skinned, brooding in minimalist dark. (LPC has no glasses item, so his black-rimmed glasses are omitted.)",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "gray"], beard: ["beards_trimmed", "gray"], clothes: ["torso_clothes_longsleeve2", "black"], legs: ["legs_formal", "black"], shoes: ["feet_boots_basic", "black"] } },
  { id: "didier-sornette", docDir: "floor-3/risk/black-swan-detection", name: "Didier Sornette", room: "risk", role: "Black Swan Detection", bodyType: "male", look: "tousled gray hair · charcoal blazer · white shirt · open collar",
    desc: "Didier Sornette's look: wavy, tousled dark-to-greying hair and a smart-casual academic blazer over an open-collared shirt — the ETH Zurich physicist who watches for dragon kings in the data. (LPC has no glasses item, so his wire-rimmed glasses are omitted.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_messy1", "gray"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "charcoal"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } }, // no tie → open collar
  { id: "var-stress-test", docDir: "floor-3/risk/var-stress-test", name: "VaR & Stress Test Agent", room: "risk", role: "VaR & Stress Test", bodyType: "male", look: "messy chestnut hair · rumpled white button-down · navy slacks",
    desc: "VaR & Stress Test Agent: the middle-office workhorse — rumpled white button-down, no tie, sleeves long gone — dreading the Friday stress-test run.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_messy1", "chestnut"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], legs: ["legs_pants2", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "correlation-concentration", docDir: "floor-3/risk/correlation-concentration", name: "Correlation & Concentration Agent", room: "risk", role: "Correlation & Concentration", bodyType: "male", look: "gray side-part · slate cardigan · brown tweed blazer · charcoal slacks",
    desc: "Correlation & Concentration Agent: the copula professor — slate cardigan under a brown tweed blazer, knowing everything goes to 1 in a crisis.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "green"], hair: ["hair_parted", "gray"], clothes: ["torso_clothes_longsleeve2_cardigan", "slate"], jacket: ["torso_jacket_collared", "brown"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "drawdown-monitor", docDir: "floor-3/risk/drawdown-monitor", name: "Drawdown Monitor Agent", room: "risk", role: "Drawdown Monitor", bodyType: "male", look: "black buzzcut · white tee · black fleece vest · dark jeans",
    desc: "Drawdown Monitor Agent: the live guard of the P&L limits — buzzcut, white tee under a black fleece vest, glued to the dashboards with a lukewarm coffee.",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], hair: ["hair_buzzcut", "black"], clothes: ["torso_clothes_tshirt", "white"], vest: ["torso_clothes_vest", "black"], legs: ["legs_pants", "black"], shoes: ["feet_shoes_basic", "white"] } },
  { id: "liquidity-risk", docDir: "floor-3/risk/liquidity-risk", name: "Liquidity Risk Agent", room: "risk", role: "Liquidity Risk", bodyType: "male", look: "neat black hair · blue button-down · charcoal suit · no tie",
    desc: "Liquidity Risk Analyst: corporate suit jacket over a slightly wrinkled blue button-down, top button undone — calculating cash-burn under a market-depth collapse.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "blue"], jacket: ["torso_jacket_collared", "charcoal"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } }, // no tie → top button undone
  { id: "factor-risk", docDir: "floor-3/risk/factor-risk", name: "Factor Risk Agent", room: "risk", role: "Factor Risk", bodyType: "male", look: "neat chestnut hair · blue shirt · navy sweater vest · charcoal slacks",
    desc: "Factor Risk Agent: clean-cut model-validation committee energy — crisp blue shirt under a navy sweater vest, watching style drift through standard deviations.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_parted", "chestnut"], clothes: ["torso_clothes_longsleeve2_buttoned", "blue"], vest: ["torso_clothes_vest", "navy"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },

  // ── Critique (Room 11) — Floor 3 Judgment ────────────────────────────────
  // Style: Reddit-researched contrarian stereotypes — the hood-up bear intern,
  // tweed-blazer inspector, sweater-vest history nerd, leather-jacket rebel,
  // beige-cardigan mediator. Named agents carry the real person's look.
  { id: "charlie-munger", docDir: "floor-3/critique/charlie-munger", name: "Charlie Munger", room: "critique", role: "Lead Critique", lead: true, bodyType: "male", look: "white hair · charcoal suit · white shirt · brown tie",
    desc: "Charlie Munger's look: thin white hair, heavy tortoiseshell glasses and the old-school charcoal suit + tie he wore every single day — the midwestern lawyer-investor who argued against everything. (LPC has no glasses item, so his iconic thick frames are omitted.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "white"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "charcoal"], tie: ["neck_necktie", "brown"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "meredith-whitney", docDir: "floor-3/critique/devils-advocate", name: "Meredith Whitney", room: "critique", role: "Devil's Advocate", bodyType: "female", look: "golden blonde bob · navy blazer · white blouse",
    desc: "Meredith Whitney's look: the golden blonde blowout and sharp navy blazer of the woman who called the crash — the analyst who said the unthinkable about Citigroup and was right.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_bob", "blonde"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "navy"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "bear-case-intern", docDir: "floor-3/critique/bear-case-intern", name: "Bear Case Intern", room: "critique", role: "Bear Case Intern", bodyType: "male", look: "hood up · gray hoodie · charcoal pants",
    desc: "Bear Case Intern: the pale, sleep-deprived doom prophet — gray hoodie up, watching the put options and waiting for the crash.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_messy1", "raven"], hat: ["hat_hood_cloth", "gray"], clothes: ["torso_clothes_longsleeve2", "gray"], legs: ["legs_pants", "charcoal"], shoes: ["feet_shoes_basic", "black"] } },
  { id: "blind-spot-detector", docDir: "floor-3/critique/blind-spot-detector", name: "Blind Spot Detector Agent", room: "critique", role: "Blind Spot Detector", bodyType: "male", look: "messy black hair · white tee · brown tweed blazer · charcoal pants",
    desc: "Blind Spot Detector Agent: the obsessive inspector — white tee under a worn brown tweed blazer, sweeping back his hair to squint at the model's blind spots.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_messy2", "black"], clothes: ["torso_clothes_tshirt", "white"], jacket: ["torso_jacket_collared", "brown"], legs: ["legs_pants", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "historical-analog-intern", docDir: "floor-3/critique/historical-analog-intern", name: "Historical Analog Intern", room: "critique", role: "Historical Analog Intern", bodyType: "male", look: "sandy hair · white shirt · green sweater vest · charcoal slacks",
    desc: "Historical Analog Intern: the history-buff nerd — green cable-knit sweater vest over an Oxford shirt, forever drawing parallels to 1929 and Tulip Mania.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "green"], hair: ["hair_parted", "sandy"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], vest: ["torso_clothes_vest", "green"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "brown"] } },
  { id: "assumption-challenger", docDir: "floor-3/critique/assumption-challenger", name: "Assumption Challenger Agent", room: "critique", role: "Assumption Challenger", bodyType: "male", look: "messy black hair · stubble · white tee · leather jacket · jeans",
    desc: "Assumption Challenger: the rebel with a rumpled leather jacket over a faded tee — stubble and a skeptical scowl, poking holes in every model.",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], hair: ["hair_messy1", "black"], beard: ["beards_5oclock_shadow", "black"], clothes: ["torso_clothes_tshirt", "white"], jacket: ["torso_jacket_collared", "leather"], legs: ["legs_pants", "blue"], shoes: ["feet_shoes_basic", "black"] } },
  { id: "conflict-resolution", docDir: "floor-3/critique/conflict-resolution", name: "Conflict Resolution Agent", room: "critique", role: "Conflict Resolution", bodyType: "male", look: "gray hair · white shirt · tan cardigan · charcoal slacks",
    desc: "Conflict Resolution Agent: the exhausted corporate mediator — neutral tan cardigan over a white shirt, keeping the peace between screaming analysts.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_balding", "gray"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], cardigan: ["torso_clothes_longsleeve2_cardigan", "tan"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },

  // ── Compliance & Tax (Room 12) — Floor 3 Judgment ───────────────────────
  // Style: the buttoned-up rule-room — conservative suits + ties, four brand-
  // new tie colors (bluegray / purple / slate / forest). Named agents carry
  // the real person's researched look.
  { id: "preet-bharara", docDir: "floor-3/compliance/preet-bharara", name: "Preet Bharara", room: "compliance", role: "Lead Compliance", lead: true, bodyType: "male", look: "slicked black hair · navy suit · white shirt · bluegray tie",
    desc: "Preet Bharara's look: slicked-back dark hair with silver streaks, medium-brown skin, and a sharp navy suit — the prosecutor who put Wall Street on notice. (LPC has no glasses item, so his glasses are omitted.)",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "navy"], tie: ["neck_necktie", "bluegray"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "h-david-rosenbloom", docDir: "floor-3/compliance/cross-border-tax", name: "H. David Rosenbloom", room: "compliance", role: "Cross-Border Tax", bodyType: "male", look: "white hair · charcoal suit · white shirt · purple tie",
    desc: "H. David Rosenbloom's look: neat white hair, thin-rimmed glasses and a charcoal suit with a muted purple tie — the elder statesman of international tax law, Treasury's former Tax Counsel. (LPC has no glasses item, so his glasses are omitted.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "white"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "charcoal"], tie: ["neck_necktie", "purple"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "regulatory-compliance", docDir: "floor-3/compliance/regulatory-compliance", name: "Regulatory Compliance Agent", room: "compliance", role: "Regulatory Compliance", bodyType: "male", look: "gray hair · navy suit · white shirt · slate tie",
    desc: "Regulatory Compliance Agent: the rule-book analyst — buttoned to the top in a navy suit and slate tie, the one who has read every regulation twice.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "gray"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "navy"], tie: ["neck_necktie", "slate"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "trading-restriction", docDir: "floor-3/compliance/trading-restriction", name: "Trading Restriction Agent", room: "compliance", role: "Trading Restriction", bodyType: "male", look: "black buzzcut · charcoal suit · white shirt · forest tie",
    desc: "Trading Restriction Agent: the window enforcer — buzzcut and a charcoal suit with a forest tie, watching every personal trade and pre-clearance request.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_buzzcut", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "charcoal"], tie: ["neck_necktie", "forest"], legs: ["legs_formal", "gray"], shoes: ["feet_boots_basic", "black"] } },

  // ── Strategy (Room 8) — Floor 4 Command ──────────────────────────────────
  // Style: where capital decisions happen — blazers and turtlenecks for the
  // leads, conservative suits + cardigan for the desk, two casual interns.
  // Named agents carry the real person's researched look.
  { id: "ray-dalio", docDir: "floor-4/strategy/ray-dalio", name: "Ray Dalio", room: "strategy", role: "Lead Strategy", lead: true, bodyType: "male", look: "silver hair · navy blazer · black turtleneck · gray slacks",
    desc: "Ray Dalio's look: short silver-white hair, clean-shaven, and a navy blazer over a black turtleneck — the Bridgewater founder's radically transparent smart-casual. (LPC has no turtleneck item — the black crew reads as his turtleneck.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "white"], clothes: ["torso_clothes_longsleeve2", "black"], jacket: ["torso_jacket_collared", "navy"], legs: ["legs_formal", "gray"], shoes: ["feet_boots_basic", "black"] } },
  { id: "david-swensen", docDir: "floor-4/strategy/asset-allocation", name: "David Swensen", room: "strategy", role: "Asset Allocation", bodyType: "male", look: "white hair · navy suit · white shirt · blue tie",
    desc: "David Swensen's look: neat white hair, glasses and a classic navy suit — the Yale endowment CIO who built the Yale model and out-returned everyone for three decades. (LPC has no glasses item, so his glasses are omitted.)",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_parted", "white"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "navy"], tie: ["neck_necktie", "blue"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "hedging-protection", docDir: "floor-4/strategy/hedging-protection", name: "Hedging & Protection Agent", room: "strategy", role: "Hedging & Protection", bodyType: "male", look: "balding gray hair · white shirt · navy cardigan · charcoal slacks",
    desc: "Hedging & Protection Agent: the cautious insurance guy — white shirt under a navy cardigan, sleeves never fully committed to anything.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "green"], hair: ["hair_balding", "gray"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], cardigan: ["torso_clothes_longsleeve2_cardigan", "navy"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "tax-optimization", docDir: "floor-4/strategy/tax-optimization", name: "Tax Optimization Agent", room: "strategy", role: "Tax Optimization", bodyType: "male", look: "black hair · charcoal suit · white shirt · rose tie",
    desc: "Tax Optimization Agent: the clever schemer — charcoal suit with a rose tie, turning tax lots into alpha.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "charcoal"], tie: ["neck_necktie", "rose"], legs: ["legs_formal", "gray"], shoes: ["feet_boots_basic", "black"] } },
  { id: "portfolio-construction", docDir: "floor-4/strategy/portfolio-construction", name: "Portfolio Construction Agent", room: "strategy", role: "Portfolio Construction", bodyType: "male", look: "sandy hair · navy suit · white shirt · walnut tie",
    desc: "Portfolio Construction Agent: the architect — navy suit and a walnut tie, building the portfolio one sleeve at a time.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "sandy"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], jacket: ["torso_jacket_collared", "navy"], tie: ["neck_necktie", "walnut"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "position-sizing-intern", docDir: "floor-4/strategy/position-sizing-intern", name: "Position Sizing Intern", room: "strategy", role: "Position Sizing Intern", bodyType: "male", look: "black bedhead hair · white button-down · navy slacks",
    desc: "Position Sizing Intern: the clean junior — white button-down, no jacket, still learning how much is too much.",
    items: { body: ["body", "brown"], eye_color: ["eye_color", "brown"], hair: ["hair_bedhead", "black"], clothes: ["torso_clothes_longsleeve2_buttoned", "white"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "brown"] } }, // no tie → open collar
  { id: "tactical-overlay-intern", docDir: "floor-4/strategy/tactical-overlay-intern", name: "Tactical Overlay Intern", room: "strategy", role: "Tactical Overlay Intern", bodyType: "male", look: "black messy hair · gray v-neck tee · blue jeans · white sneakers",
    desc: "Tactical Overlay Intern: the short-term guy — gray v-neck, jeans and sneakers, overlaying the tactical bets on top of the long-term plan.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_messy1", "black"], clothes: ["torso_clothes_tshirt_vneck", "gray"], legs: ["legs_pants", "blue"], shoes: ["feet_shoes_basic", "white"] } },

  // ── Execution (Room 9) — Floor 4 Command ─────────────────────────────────
  // Style: the dark execution desk — midnight blues, charcoal, black, one
  // khaki-polo checklist operator. Everyone distinct: no shared hair+shirt
  // combo. Named agent carries the real person's researched look.
  { id: "vlad-tenev", docDir: "floor-4/execution/vlad-tenev", name: "Vlad Tenev", room: "execution", role: "Lead Execution", lead: true, bodyType: "male", look: "neat black hair · charcoal blazer · black turtleneck · gray slacks",
    desc: "Vlad Tenev's look: neat dark hair, clean-shaven, and the dark minimalist blazer over a black turtleneck — Robinhood's co-founder, the zero-commission execution man who lives on the fill times. (LPC has no watch item, so his rose-gold Rolex is omitted.)",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_parted", "black"], clothes: ["torso_clothes_longsleeve2", "black"], jacket: ["torso_jacket_collared", "charcoal"], legs: ["legs_formal", "gray"], shoes: ["feet_boots_basic", "black"] } },
  { id: "order-routing", docDir: "floor-4/execution/order-routing", name: "Order Routing Agent", room: "execution", role: "Order Routing", bodyType: "male", look: "buzzcut · navy polo · charcoal slacks",
    desc: "Order Routing Agent: the order-flow babysitter — navy polo, buzzcut, one eye on the blotter and one on the headset, routing every ticket to the venue without spilling it.",
    items: { body: ["body", "olive"], eye_color: ["eye_color", "brown"], hair: ["hair_buzzcut", "black"], clothes: ["torso_clothes_shortsleeve_polo", "navy"], legs: ["legs_formal", "charcoal"], shoes: ["feet_boots_basic", "black"] } },
  { id: "execution-algorithm", docDir: "floor-4/execution/execution-algorithm", name: "Execution Algorithm Agent", room: "execution", role: "Execution Algorithm", bodyType: "male", look: "messy dark hair · forest v-neck tee · navy pants · black sneakers",
    desc: "Execution Algorithm Agent: the speed hacker — forest v-neck tee and navy pants, tuned to shave microseconds off every fill and outsmart the queue.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "green"], hair: ["hair_messy1", "raven"], clothes: ["torso_clothes_tshirt_vneck", "forest"], legs: ["legs_pants", "navy"], shoes: ["feet_shoes_basic", "black"] } },
  { id: "timing-slippage", docDir: "floor-4/execution/timing-slippage", name: "Timing & Slippage Agent", room: "execution", role: "Timing & Slippage", bodyType: "male", look: "messy sandy hair · charcoal button-down · navy slacks",
    desc: "Timing & Slippage Agent: the microsecond-obsessed one — rumpled sandy hair, charcoal button-down, muttering about implementation shortfall and the spread that got away.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "blue"], hair: ["hair_bedhead", "sandy"], clothes: ["torso_clothes_longsleeve2_buttoned", "charcoal"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "black"] } },
  { id: "pre-flight-check", docDir: "floor-4/execution/pre-flight-check", name: "Pre-Flight Check Agent", room: "execution", role: "Pre-Flight Check", bodyType: "male", look: "gray hair · walnut polo · navy slacks",
    desc: "Pre-Flight Check Agent: the launch-checklist operator — khaki-walnut polo, clipboard discipline, running the pre-trade checks a hundred times before any order gets the green light.",
    items: { body: ["body", "light"], eye_color: ["eye_color", "brown"], hair: ["hair_balding", "gray"], clothes: ["torso_clothes_shortsleeve_polo", "walnut"], legs: ["legs_formal", "navy"], shoes: ["feet_boots_basic", "brown"] } },
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
    // Unisex fallback: some garments (vests, jacket_collared, ...) only ship a
    // male sprite in the LPC set — use it for female bodies too rather than
    // silently dropping the layer (deskrpg's getLayerPaths would skip it).
    let base = ld.paths[bodyType] ?? ld.paths.male;
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
