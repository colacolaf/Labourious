// ---------------------------------------------------------------------------
// agent-cards.js — shared building blocks for every agent roster page
// (agent-gallery.html, research-agents.html, sentiment-agents.html, ...).
//
// Room pages only need to: link agent-cards.css, import loadManifest /
// appendAgentCard / showError, filter agents by room, and append cards.
// ---------------------------------------------------------------------------

import { compositeCharacter, drawStandstill, FRAME_WIDTH } from "./agent-compositor.js";

// Display titles per room id (fall back to uppercase id in the gallery).
export const ROOM_TITLES = {
  examples:  "EXAMPLES",
  research:  "RESEARCH · ROOM 1",
  sentiment: "SENTIMENT · ROOM 7",
  altdata:   "ALTERNATIVE DATA · ROOM 13",
  quant:     "QUANT · ROOM 4",
  perimeter: "PERIMETER · GROUND FLOOR",
  penthouse: "PENTHOUSE · THE TOP",
  crypto:    "CRYPTO · ROOM 14",
  fundamental: "FUNDAMENTAL · ROOM 5",
  macro:     "MACRO · ROOM 3",
  technical: "TECHNICAL · ROOM 6",
  risk:      "RISK · ROOM 2",
  critique:  "CRITIQUE · ROOM 11",
  compliance: "COMPLIANCE & TAX · ROOM 12",
  strategy:  "STRATEGY · ROOM 8",
  execution: "EXECUTION · ROOM 9",
  memory:    "MEMORY · ROOM 10",
  control:   "CONTROL · ROOM 15",
  tasks:     "TASKS · ROOM 16",
};

export function roomTitle(room) {
  return ROOM_TITLES[room] ?? room.toUpperCase();
}

export async function loadManifest() {
  // Cache-bust the manifest fetch (the dev server sends long-lived cache
  // headers), then append the build version to every layer PNG URL — a stale
  // cached agents.json is exactly how an old look keeps showing up after a
  // rebuild. Tolerates the old plain-array manifest shape too.
  const res = await fetch("/assets/agents/agents.json?bust=" + Date.now());
  if (!res.ok) throw new Error("HTTP " + res.status);
  const json = await res.json();
  const agents = json.agents ?? json;
  if (json.version) {
    for (const a of agents) for (const l of a.layers) l.src += "?v=" + json.version;
  }
  return agents;
}

export function showError(container, err) {
  container.textContent = "";
  const el = document.createElement("div");
  el.className = "error";
  el.textContent = "Failed to load agent roster: " + err.message;
  container.appendChild(el);
}

/**
 * Build one agent card (canvas standstill + name + role + look) and append
 * it to `container`. Lead agents get a gold border and a ★ LEAD badge.
 */
export async function appendAgentCard(container, agent, { scale = 4 } = {}) {
  const card = document.createElement("div");
  card.className = "card" + (agent.lead ? " lead" : "");

  if (agent.lead) {
    const badge = document.createElement("div");
    badge.className = "badge";
    badge.textContent = "★ LEAD";
    card.appendChild(badge);
  }

  const canvas = document.createElement("canvas");
  canvas.width  = FRAME_WIDTH * scale;
  canvas.height = FRAME_WIDTH * scale;

  const sheet = document.createElement("canvas");
  await compositeCharacter(sheet, agent.layers);
  drawStandstill(canvas, sheet, { scale });

  const name = document.createElement("div");
  name.className = "name";
  name.textContent = agent.name.toUpperCase();

  const role = document.createElement("div");
  role.className = "role";
  role.textContent = agent.role;

  const look = document.createElement("div");
  look.className = "look";
  look.textContent = agent.look;

  card.append(canvas, name, role, look);
  container.appendChild(card);
}
