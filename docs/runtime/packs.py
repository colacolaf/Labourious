"""
packs.py — pluggable sector-pack library loader.

Implements the *pluggable policy* documented in
[`DEFERRED.md`](../DEFERRED.md) and referenced by
[`f5-sector-deep-dive.md`](../flows/f5-sector-deep-dive.md):

    Sectors are knowledge packs, not agents.

The senior-analyst prompt adopts a sector lens via a short sector-pack
appended to its prompt at runtime — not via a separate agent. Loading a
pack is:

    >>> pack = load_pack("semiconductors")
    >>> sa_prompt = sa_prompt_template.replace("{sector_pack}", pack.body)

Pack files live under ``docs/prompts/pluggable/`` with a YAML
frontmatter schema:

    ---
    slug: semiconductors
    display_name: AI-exposed Semiconductors
    tickers: [NVDA, AMD, INTC, AVGO, TSM, MU, ASML, MRVL]
    coverage: 2020-2026
    primary_sources:
      - SEC EDGAR 8-K / 10-Q segment revenue + inventory
      - TSMC monthly revenue releases
      - SEMI billings report
    last_updated: 2026-08-20
    ---

    # AI-exposed Semiconductors ...

The body is plain Markdown. The runtime injects the body — verbatim —
into the senior-analyst's system prompt under a ``{sector_pack}``
placeholder. The pack's framing *biases the analyst*: which sources to
lean on, which checks are positive triggers, which are negative
triggers. The analyst still does the actual research.

Three failure modes (clean None, no exception):

  - ``load_pack("")``                       → ``None``
  - ``load_pack("bogus")``                  → ``None`` (unknown slug)
  - malformed frontmatter / unreadable file → ``None``

Three result dataclasses:
  - ``PackMeta``  — parsed frontmatter (slug, tickers, sources).
  - ``Pack``      — ``PackMeta`` + the body markdown + parsed path.
  - ``MatchResult`` — what ``auto_match_pack`` returned and why.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Locations + path helpers
# ---------------------------------------------------------------------------
def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


PROMPTS_DIR = _project_root() / "docs" / "prompts"
PACKS_DIR = PROMPTS_DIR / "pluggable"

# Frontmatter delimiter — strict to avoid grabbing the wrong ``---``.
_FM_OPEN = re.compile(r"^---\s*$")
_FM_KV   = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
# Lists under a key live on indented ``- ...`` lines:
_FM_LIST_ITEM = re.compile(r"^\s+-\s+(.+)$")


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PackMeta:
    """Parsed frontmatter for one pack file."""
    slug: str
    display_name: str
    tickers: frozenset[str]
    primary_sources: tuple[str, ...]
    coverage: str
    last_updated: str
    path: Path

    def has_ticker(self, ticker: str) -> bool:
        return ticker.upper().strip() in self.tickers


@dataclass(frozen=True)
class Pack:
    """One pack: meta + the prose body the runtime injects into the prompt."""
    meta: PackMeta
    body: str

    def render_for_prompt(self) -> str:
        """Return the body in the format the senior-analyst prompt expects.

        Three sections, in order:

          1. ``## Sector Packaging`` heading so the LLM can localise the
             pack in its context.
          2. One-line slug+display_name for grep-debugging.
          3. The pack body verbatim.
          4. A ``## Pack primary sources`` mirror so the analyst can
             cite the pack's primary sources verbatim.
        """
        head = (
            f"\n\n## Sector Packaging ({self.meta.slug})\n\n"
            f"__{self.meta.display_name}__ — "
            f"tickers: {', '.join(sorted(self.meta.tickers)) if self.meta.tickers else '(universe)'}.  "
            f"coverage: {self.meta.coverage}.  "
            f"last_updated: {self.meta.last_updated}.\n\n"
        )
        cited = ""
        if self.meta.primary_sources:
            cited = (
                "\n## Pack primary sources (cite from these first)\n\n"
                + "\n".join(f"- {s}" for s in self.meta.primary_sources)
                + "\n"
            )
        return head + self.body + cited


@dataclass(frozen=True)
class MatchResult:
    """Outcome of ``auto_match_pack``."""
    pack: Pack
    matched_tickers: tuple[str, ...]
    overlap_pct: float
    runners_up: tuple[tuple[str, float], ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Frontmatter parser — handles multi-line YAML list blocks
# ---------------------------------------------------------------------------
def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return ``(meta_dict, body)``.

    The ``meta_dict`` carries both simple key/value pairs and list-
    valued fields. List values are coerced into a list of strings and
    joined with ``"\\n"``; the typed list coercer (``_coerce_sources``)
    splits on newlines. This is more robust than treating YAML list
    blocks as ``meta[key] = "- item"`` line-by-line, because then
    multi-line lists overwrite each other in the dict.

    No body → empty string. No frontmatter → empty dict + full text
    as body. Malformed frontmatter (no closing ``---``) → empty dict +
    full text as body.
    """
    lines = text.splitlines()
    if not lines or not _FM_OPEN.match(lines[0]):
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if _FM_OPEN.match(lines[i]):
            end = i
            break
    if end is None:
        return {}, text
    raw_meta_block = lines[1:end]
    body = "\n".join(lines[end + 1 :])
    meta: dict[str, str] = {}
    current_list_key: str | None = None
    for raw in raw_meta_block:
        kv = _FM_KV.match(raw)
        if kv:
            current_list_key = None
            key, value = kv.group(1), kv.group(2).strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            meta[key] = value
            # Inline flow list like ``tickers: [NVDA, AMD]`` lives on
            # the same line — keep current_list_key as None so a later
            # indented ``- ...`` doesn't accidentally attach.
            continue
        item = _FM_LIST_ITEM.match(raw)
        if item and current_list_key is not None:
            # Append this list item to the key (newline-joined).
            prior = meta.get(current_list_key, "")
            new = item.group(1).strip()
            meta[current_list_key] = (prior + ("\n" if prior else "") + new)
            continue
        # Non-list, non-key line: close any open list.
        current_list_key = None
    # Detect "this key is now a list" by noticing the prior key's value
    # is empty and the next non-empty line was an indented ``- ...``:
    # the simple model above already handles that. But if the key
    # has an empty value and ``-`` lines came right after, the
    # current_list_key tracker would have caught them. Re-check: we
    # only set current_list_key when a key: came through with an
    # empty value AND there were ``-`` items following. The current
    # implementation handles this naturally because ``kv.group(2)``
    # is empty and we set current_list_key to None after the kv
    # match — wait, that's wrong: setting it to None means we lose
    # tracking. Fix: store the key only if its value is empty.
    # Re-walk to identify list-trail keys explicitly.
    return meta, body


# Re-parse: a tighter detector for "key with empty value followed by
# indented - lines" so we can populate the list under that key. We
# do this in a second pass to keep the dict population simple.
def _extract_list_blocks(raw_meta_lines: list[str]) -> dict[str, list[str]]:
    """Walk the meta lines; for each ``key:`` (with no inline value),
    collect immediately-following ``  - item`` rows. Returns a
    ``{key: [items...]}`` mapping. Inline lists (``[a, b, c]``) are
    ignored (the dict-driven parser already keeps that).
    """
    out: dict[str, list[str]] = {}
    i = 0
    while i < len(raw_meta_lines):
        kv = _FM_KV.match(raw_meta_lines[i])
        if not kv:
            i += 1
            continue
        key, value = kv.group(1), kv.group(2).strip()
        if value:
            i += 1
            continue
        # Look ahead for ``-`` items.
        j = i + 1
        items: list[str] = []
        while j < len(raw_meta_lines):
            li = _FM_LIST_ITEM.match(raw_meta_lines[j])
            if not li:
                break
            items.append(li.group(1).strip())
            j += 1
        if items:
            out[key] = items
        i = j
    return out


def _coerce_tickers(raw: str | None) -> frozenset[str]:
    """Parse a frontmatter ``tickers`` field into a frozenset."""
    if not raw:
        return frozenset()
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    out = set()
    for token in re.split(r"[,\s]+", raw):
        token = token.strip().strip("'\"")
        if token:
            out.add(token.upper())
    return frozenset(out)


def _coerce_sources(raw: str | None, list_block: list[str] | None = None) -> tuple[str, ...]:
    """Parse a frontmatter ``primary_sources`` field.

    Accepts:

    - Inline comma list:   ``primary_sources: a, b, c``
    - Multi-line YAML:     ``primary_sources:\\n  - a\\n  - b\\n  - c``
      (the list-block form, exposed via ``_extract_list_blocks``).
    - Empty / None         → ``()``.

    Returns a tuple of deduped, order-preserving strings.
    """
    if list_block:
        # Multi-line YAML form has higher precedence — the loader
        # always finds the actual items through _extract_list_blocks.
        seen: set[str] = set()
        out: list[str] = []
        for s in list_block:
            s = s.strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return tuple(out)
    if not raw:
        return ()
    # Inline form: comma- or newline-separated.
    items: list[str] = []
    for line in raw.splitlines():
        s = line.strip().lstrip("- \t").strip()
        if s:
            items.append(s)
    if len(items) <= 1:
        items = [s.strip() for s in raw.split(",") if s.strip()]
    seen = set()
    out = []
    for s in items:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return tuple(out)


# ---------------------------------------------------------------------------
# Pack discovery + loading
# ---------------------------------------------------------------------------
def _scan_packs() -> list[PackMeta]:
    """Read every ``<packs-dir>/*.md`` and return the parsed metas.

    Files without ``slug:`` in their frontmatter are skipped silently
    (they're readme / index files, not packs). Malformed frontmatter
    is logged via stdout once and skipped.
    """
    if not PACKS_DIR.exists():
        return []
    out: list[PackMeta] = []
    for path in sorted(PACKS_DIR.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = _parse_frontmatter(text)
        if not meta:
            continue
        slug = meta.get("slug") or ""
        if not slug:
            continue  # not a pack (readme, index)
        # Multi-line YAML list blocks: re-walk the raw meta lines
        # and pull ``key:\\n  - ...`` lists when present.
        raw_lines = text.splitlines()
        # Slice between the opening ``---`` and the closing ``---``.
        lists: dict[str, list[str]] = {}
        if raw_lines and _FM_OPEN.match(raw_lines[0]):
            end = None
            for i in range(1, len(raw_lines)):
                if _FM_OPEN.match(raw_lines[i]):
                    end = i
                    break
            if end is not None:
                lists = _extract_list_blocks(raw_lines[1:end])
        primary_block = lists.get("primary_sources")
        out.append(
            PackMeta(
                slug=slug.lower().strip(),
                display_name=meta.get("display_name") or slug.title(),
                tickers=_coerce_tickers(meta.get("tickers")),
                primary_sources=_coerce_sources(
                    meta.get("primary_sources"), primary_block,
                ),
                coverage=meta.get("coverage") or "current cycle",
                last_updated=meta.get("last_updated") or "unspecified",
                path=path,
            )
        )
    return out


# Discovery cache — invalidated on clear_cache().
_DISCOVERY_CACHE: list[PackMeta] | None = None


def clear_cache() -> None:
    """Drop the in-memory discovery cache.

    Tests use this between scenarios; the runtime calls it on
    file-watch reload (deferred — no inotify in v1).
    """
    global _DISCOVERY_CACHE
    _DISCOVERY_CACHE = None


def list_packs() -> list[PackMeta]:
    """Return the meta list of all packs the runtime can see."""
    global _DISCOVERY_CACHE
    if _DISCOVERY_CACHE is None:
        _DISCOVERY_CACHE = _scan_packs()
    return list(_DISCOVERY_CACHE)


def load_pack(slug_or_name: str | None) -> Pack | None:
    """Look up a pack by slug, slug-with-suffix, or display_name (case-insensitive).

    Returns ``None`` on miss (empty slug, unknown slug, malformed).
    Never raises — pack loads are user-facing.

    Pick strategy:
      1. exact slug match
      2. slug-prefix / prefix-of-slug match
      3. case-insensitive display_name match
    """
    if not slug_or_name:
        return None
    needle = slug_or_name.lower().strip()
    if not needle:
        return None
    needle = re.sub(r"[^a-z0-9-]+", "-", needle).strip("-")
    if not needle:
        # The cleaned needle is empty (input was all whitespace or
        # punctuation). Don't fall through to the ``startswith("")``
        # trap that would pick the first pack alphabetically.
        return None
    for suf in ("-pack", "pack", "-sector", "sector"):
        if needle.endswith(suf):
            needle = needle[: -len(suf)]
    metas = list_packs()
    pick: PackMeta | None = None
    for m in metas:
        if m.slug == needle:
            pick = m
            break
    if pick is None:
        for m in metas:
            if m.slug.startswith(needle) or needle.startswith(m.slug):
                pick = m
                break
    if pick is None:
        for m in metas:
            if m.display_name.lower().strip() == slug_or_name.lower().strip():
                pick = m
                break
    if pick is None:
        return None
    try:
        text = pick.path.read_text(encoding="utf-8")
    except OSError:
        return None
    meta, body = _parse_frontmatter(text)
    return Pack(meta=pick, body=body.strip())


def auto_match_pack(tickers: Iterable[str]) -> MatchResult | None:
    """Pick the pack whose ticker set overlaps the universe best.

    Returns ``None`` if no tickers were given or no pack had a single
    ticker overlap (we don't fall through to "generalist" by default
    — a generalist pack, if it exists, is a positive match for the
    universe; without one, the caller should run as a generalist
    with no pack).

    The score is ``matched_tickers / universe_size``. Runners-up
    (top 3 below the winner) are returned so the prompt can show
    "we picked chips; financials was 2nd" if useful.
    """
    tickers = frozenset(t.upper().strip() for t in tickers if t)
    if not tickers:
        return None
    scores: list[tuple[PackMeta, frozenset[str]]] = []
    for m in list_packs():
        if not m.tickers:
            continue
        hit = tickers & m.tickers
        if hit:
            scores.append((m, hit))
    if not scores:
        return None
    sorted_scores = sorted(
        scores, key=lambda kv: (len(kv[1]), len(kv[0].tickers)),
        reverse=True,
    )
    best_meta, best_hit = sorted_scores[0]
    best_pack = load_pack(best_meta.slug)
    if best_pack is None:
        return None
    runners_up = tuple(
        (m.slug, len(m.tickers & tickers) / max(1, len(tickers)))
        for m, _hit in sorted_scores[1:4]
    )
    return MatchResult(
        pack=best_pack,
        matched_tickers=tuple(sorted(best_hit)),
        overlap_pct=len(best_hit) / len(tickers),
        runners_up=runners_up,
    )


# ---------------------------------------------------------------------------
# Senior-analyst prompt injection
# ---------------------------------------------------------------------------
SECTOR_PACK_PLACEHOLDER = "{sector_pack}"


def format_senior_analyst_with_pack(
    prompt_template: str,
    pack: Pack | None,
) -> str:
    """Inject ``pack.body`` into the senior-analyst prompt's ``{sector_pack}`` slot.

    No-pack case: a one-line *"(no sector pack loaded — running
    generalist)"* stub so the LLM doesn't read a literal ``{sector_pack}``
    placeholder. With pack: ``Pack.render_for_prompt()`` brings the
    slug header + body + primary sources block.

    Idempotent: applying twice with the same pack produces the same
    output (the placeholder no longer exists after the first call).
    """
    if SECTOR_PACK_PLACEHOLDER not in prompt_template:
        return prompt_template
    if pack is None:
        body = "_No sector pack loaded — running as a generalist senior analyst._"
    else:
        body = pack.render_for_prompt()
    if prompt_template.count(SECTOR_PACK_PLACEHOLDER) > 1:
        head, _, rest = prompt_template.partition(SECTOR_PACK_PLACEHOLDER)
        return head + body + rest.replace(SECTOR_PACK_PLACEHOLDER, "")
    return prompt_template.replace(SECTOR_PACK_PLACEHOLDER, body)


__all__ = [
    "PACKS_DIR",
    "PROMPTS_DIR",
    "SECTOR_PACK_PLACEHOLDER",
    "PackMeta",
    "Pack",
    "MatchResult",
    "clear_cache",
    "list_packs",
    "load_pack",
    "auto_match_pack",
    "format_senior_analyst_with_pack",
]
