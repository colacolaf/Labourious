---
slug: semiconductors
display_name: AI-exposed Semiconductors
tickers: [NVDA, AMD, INTC, AVGO, TSM, MU, MRVL, ASML]
coverage: 2020-01 → current cycle
primary_sources:
  - SEC EDGAR form 8-K / 10-Q segment revenue + inventory disclosures
  - TSMC monthly revenue release (Taiwan Stock Exchange)
  - SIA (Semiconductor Industry Association) global billings report
  - DRAM spot price index (DRAMeXchange / TrendForce)
  - Hyperscaler capex guidance (Microsoft / Alphabet / Amazon / Meta 10-Qs)
  - ASML system bookings disclosure (10-Q and quarterly call deck)
last_updated: 2026-08-20
---

# Sector Pack — AI-exposed Semiconductors

## Bottom line framing

This sector's P&L is a leveraged proxy for AI capex. Two axes decide
cycle stage:

1. **Hyperscaler capex guidance** (the demand pulse). When Microsoft
   / Alphabet / Amazon / Meta raise full-year capex, it's a 6–9
   month leading indicator for foundry and accelerator demand.
2. **Inventory + book-to-bill** (the supply pulse). When foundries
   and DRAM makers carry rising inventory *and* book-to-bill has
   rolled under 1.0 for 2 quarters, the cycle is past peak regardless
   of what management says on the call.

The senior analyst's job on any name in this pack: locate the name on
each axis independently, then ask "what would break my read?" before
writing a direction.

## Per-name sector-position rubric

| Ticker | Sub-segment | Cycle position cue | Source-of-truth check |
|--------|-------------|--------------------|------------------------|
| NVDA | AI accelerators | Datacenter segment YoY + customer concentration (top 4 = 30%+ risk) | 10-K Note: customer concentration; 10-Q segment revenue |
| AMD | CPU + accelerator | Datacenter + client YoY; MI300 ramp commentary | 10-Q segment trends; Lisa Su's quarterly call |
| INTC | CPU + foundry | IFS external wins; 18A node yield commentary | 10-Q IFS revenue; quarterly capex |
| AVGO | Custom silicon + networking | AI revenue (+ custom accelerator track); VMware attach | 10-Q segment: "AI revenue" line (started FY24) |
| TSM | Foundry | Monthly revenue YoY; 3nm revenue mix; leading-edge utilization | TSMC monthly (11th of month, T+15 days) |
| MU | DRAM / NAND | DRAM spot pricing; inventory days on call; HBM qualification | 10-Q: inventory + days; spot index |
| MRVL | Custom silicon + networking | Cloud capex commentary; revenue guide | 10-Q "Data Center" segment + guide |
| ASML | Lithography | Net system bookings; EUV vs DUV split; China exposure | 10-Q "Net system bookings" + China revenue disclosure |

## Sources to lean on (priority order)

1. **Filing date + segment table** — first read, every time. Last
   quarter's segment table is the source-of-truth; if you'd say the
   cycle it turning and the segment table contradicts, defer to the
   table.
2. **TSMC monthly for foundry pulse** — beats the SIA by 6 weeks. If
   TSMC YoY rolls negative two months in a row, the cycle turn is
   imminent for everyone downstream.
3. **Hyperscaler capex signalling** — read *forward 12-month* capex
   lines from MSFT / GOOGL / AMZN / META 10-Qs, not quarter-by-quarter
   beats. The *level* matters less than the *slope*.
4. **Management-prepared remarks vs Q&A** — disagree by design.
   Remarks smooth; Q&A reveals nuance. Cite Q&A when you need a
   disclosure, remarks when you need a tone read.
5. **Channel checks** — only one tier-1 primary source: TrendForce /
   DRAMeXchange spot. Free-tier aggregates are 2-week lagged.

## Bidirectional triggers

### Positive triggers (each adds conviction)

- Hyperscaler capex guide raised + TSMC MoM YoY positive ⇒ fortress
  sector read across NVDA / AMD / AVGO / MRVL / ASML.
- Net system bookings at ASML return above €8B/quarter ⇒ EUV cycle
  has legs; foundry ramp not over.
- Customer concentration disclosure without an obvious single-customer
  over 20% ⇒ management is comfortable; signal positive.
- Inventory days improving quarter-on-quarter *and* book-to-bill
  above 1.0 ⇒ cycle bottom is in, name(s) levered to upturn.

### Negative triggers (each erodes conviction)

- TSMC MoM revenue YoY negative 2 months running ⇒ foundry demand
  pulse broken; assume lag = 1 quarter for downstream names.
- Single customer >25% of revenue newly disclosed ⇒ concentration
  risk and *also* sign the company is selling forward. Both reads
  valid; flag for devils-advocate.
- Inventory days rising + book-to-bill below 1.0 for 2 quarters ⇒
  management's "we see a recovery Q3" guidance is wishful; treat
  the cycle as past peak until proven.
- China revenue disclosure rising while export-control discussion
  intensifies ⇒ the upside is real but politically time-limited.

## Common biases to watch for

- **Capex-mirroring bias**: analysts (and LLMs) reflexively move NVDA
  on *any* AI headline. Decouple: hyperscaler capex guide is the
  trigger, product launches are not. A new chip without a customer
  attached is press release, not demand.
- **Cycle amnesia**: this sector has had 5–7 booms in 25 years. Every
  peak is "different this time." It's not, until a structural change
  is disclosed in a 10-K (new customer, new segment, new margin
  profile). Don't soften the bearish read on assumption of
  permanently-improved economics.
- **Foundry-vs-fabless conflation**: finding NVDA weak but TSMC strong
  is meaningless — they're not the same wave. Fit the name to the
  axis correctly first, *then* write the read.
- **EUV vs DUV opacity**: ASML net system bookings rolls EUV +
  advanced DUV together. Don't interpret a 30% bookings fall as
  "the EUV cycle is over" — it usually isn't.
- **Memory cycle is its own thing**: MU is NOT a leading indicator for
  NVDA. Memory and logic run separate cycles 18–24 months apart. Bad
  read: "DRAM down ⇒ everything down." Good read: cite the spot index
  separately.

## What "good" looks like vs what the typical sell-side model says

| Metric | Sell-side default | Pack would prefer |
|--------|-------------------|-------------------|
| Cycle peak signal | "Inventory normalized" | Inventory days + book-to-bill *both* improving |
| NVDA valuation | Forward P/E vs FY+1 EPS | Forward P/E vs capex-implied ASP × unit run-rate |
| TSM growth | YoY % | YoY % × (revenue mix shift to leading edge) |
| Inventory read | Days outstanding | Days + absolute inventory YoY $ — if both rise, the read is excess not smoothing |
| Cyclical trough signal | Bookings inflection | Bookings *and* customer-funded wafer starts |

## What an attacker would say about this pack

- "You overweight hyperscaler capex as a signal. The hyperscaler capex
  is increasingly tied up with their own custom silicon (AVGO / MRVL
  / INTC 18A wins) — so the 'AI demand' fog is getting harder to
  read. Your segment-table discipline fights this; without it the
  pack degenerates into press-release-reading."
- "TSMC monthly is a great signal but it's lagging the cycle by
  exactly when you need to act — the foundry's leading-edge
  utilization drops *before* monthly revenue does. The pack reads
  monthly rather than earnings-prepared-remarks for this reason and
  it costs you a quarter in the inflection trade."
- "You underplay export controls. China exposure discussions now
  shift the realized-revenue line for ASML, TSM, MU within a quarter.
  Your pack handles this via 'China revenue disclosure' but not
  explicitly via revenue attribution by region at the cycle-peak
  line. A tighter version would force a 'where does the $ come
  from?' decomposition before any cycle read."
- "The 'common biases' section is honest but it doesn't gate them.
  An agent following this pack can write a capex-mediated, well-
  sourced thesis and STILL miss the cycle — the biases named
  don't include 'I read the segment table but I trusted my eyes
  over the math.' Add the gate."

## Pack failure modes (when to abandon this lens)

- The name has < 30 % of revenue in the segments the pack covers
  (avoid reading e.g. INTC's PSG: not this pack's beat).
- The cycle is so compressed that monthly data is older than the
  news cycle. In that case: prioritize hyperscaler-side filings,
  abandon the foundry-side monthly read.
- Hyperscaler capex is broadly flat for 4 consecutive quarters.
  Means the cycle is in *consolidation*, not upturn, not downturn.
  Pack becomes noise generator — pull back to generalist read.

## Citations

- SEC EDGAR company filings (form 8-K, 10-K, 10-Q)
  https://www.sec.gov/cgi-bin/browse-edgar
- TSMC monthly revenue release (Taiwan Stock Exchange)
  https://investor.tsmc.com/english/monthly-revenue
- SIA — Semiconductor Industry Association global billings
  https://www.semiconductors.org/industry-statistics/
- TrendForce DRAMeXchange spot pricing
  https://www.trendforce.com/
- Hyperscaler 10-Q capex disclosure (MSFT / GOOGL / AMZN / META)
- ASML — Investor Relations quarterly "Net system bookings"
  https://www.asml.com/en/investors

---

_pack v2026-08-20 · opinionated analyst framing; not financial advice_
