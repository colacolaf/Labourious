---
slug: banks
display_name: US Money-Center + Regional Banks
tickers: [JPM, BAC, WFC, C, GS, MS, USB, PNC, SCHW]
coverage: 2014 stress-test cycle → current cycle
primary_sources:
  - Federal Reserve / OCC stress test (CCAR / DFAST) results
  - SEC 10-K / 10-Q: net charge-off (NCO) trends, ACL build/release
  - Form FR Y-9C (large bank holding companies) — Consolidated Financial Statements
  - FRED — H.8 bank credit, H.15 yield curve, M.2 money supply
  - FDIC Quarterly Banking Profile (all commercial banks aggregate)
  - Each name's investor day deck (5-year targets) — only with skepticism
last_updated: 2026-08-20
---

# Sector Pack — US Money-Center + Regional Banks

## Bottom line framing

Banks are not a thesis business. They're a **carry + NCO + ACL**
business and nothing else. Every sentence in a bank-stress thesis
should reduce to one of three things:

1. **Net interest margin (NIM) direction** — driven by the slope of
   the yield curve (2s10s, 30y/3m), the deposit beta, and the
   asset-mix shift into securities at lower yields.
2. **Net charge-off (NCO) cycle** — the loss-side pulse. ACL build or
   release drives reported earnings, but the *level* of NCO vs pre-
   provision NCO is what matters. Reported EPS includes "good bank"
   dynamics that mask real portfolio deterioration.
3. **Capital adequacy vs CCR stress loss** — the regulator-published
   stress loss dictates the captive capital ratio. If the holdco
   CET1 is within 100 bps of the regulatory minimum after the
   stress loss, the bank's buyback programme is hollow.

Three things that LOOK important but aren't:

- Reported EPS y/y growth (always partial; recasts ACL).
- Revenue line (always noisy; treasury-trading desks can swing $1B
  in a week).
- Loan growth % (this is *gross*; doesn't reflect payoff of higher-
  rate vintages or charge-offs).

## Per-name sector-position rubric

| Ticker | Sub-segment | Cycle position cue | Source-of-truth check |
|--------|-------------|--------------------|------------------------|
| JPM | Money-center | All three: NIM, NCO, capital. They publish 2025 NII guide each Jan. | Investor day; 10-Q NII + ACL lines |
| BAC | Money-center | NIM curve + CRE (commercial real estate) exposure | 10-Q NII + ACL; CRE/office CRE % |
| WFC | Regional-turned-NB | Deposit beta (still high); asset-cap removal cue | 10-Q; 8-K consent orders updates |
| C | Money-center | NIM + trading-revenue mix | 10-Q NII + Markets revenue line |
| GS | Investment-bank-led | Capital Markets + Investment Banking revenue (cycle proxy) | 10-Q Capital Markets + Investment Banking segments |
| MS | IB-led | Same vector as GS + Wealth Management coupon compounding | 10-Q Wealth Management segment |
| USB | Regional | NIM + CRE concentration (US Bank Tower-era CRE scars) | 10-Q NII + CRE concentration table |
| PNC | Regional | NIM + mid-market CRE | 10-Q; segment: "Corporate Banking" |
| SCHW | Repo / brokerage | NIM + cash-sortie rate (deposit beta ~ 90% of sweep) | 10-Q + 13F-style "Bank Sweep" disclosure |

## Sources to lean on (priority order)

1. **FFIEC Call Report / FR Y-9C** — the regulator's audited picture.
   Different from 10-K by exactly one quarter. Read both. The 10-Q
   glosses over regional CRE; the Y-9C breaks it out by metro.
2. **FRED H.8 (bank credit)** — the *aggregate* pulse. When H.8
   commercial loan YoY rolls negative, the cycle is in upturn (the
   loan demand pulse precedes earnings by 6–9 months).
3. **2s10s curve** — what *banks* think the next NIM direction is, not
   what economists think. If 2s10s is at -50 bps, NII guidance from
   JPM = bear-range. If +100 bps, its guidance = neutral.
4. **Stress test (CCAR / DFAST)** — the regulator-published stress
   loss *adjusts* the basis of any capital analysis. Never model
   capital headroom without referencing the published stress loss for
   the latest cycle year.
5. **Form 8-K consent-order updates** — what can sell; what can't.
   The WFC asset cap is the headline example but every regional bank
   has a consent-order tail.
6. **FDIC Quarterly Banking Profile** — aggregate picture; spot checks
   for retail deposit outflows vs the aggregate.

## Bidirectional triggers

### Positive triggers

- 2s10s curve positive + deposit beta stable ⇒ NIM is in upturn; bias
  positive on money-centers with high deposit share (WFC, USB).
- NCO trends stable at < 50 bps of avg loans (pre-2022 baseline) +
  ACL coverage > 1.5x NCO ⇒ pre-provision earnings are real.
- Stress test loss in the published scenario is < 5% of capital +
  CET1 > 12% post-stress ⇒ buyback is meaningful, not performative.
- Sponsor-loan pipeline (PE-led) re-accelerating ⇒ large-loan demand
  pulse back; positive for CIB banks (JPM / C / GS / MS).
- Wealth-management NNA (net new assets) positive for 4 quarters ⇒
  multi-year fee compounding; positive for MS / GS / USB "UHNW" lines.

### Negative triggers

- 2s10s curve < -50 bps + rate-cut cycle clear ⇒ NIM compression is
  durable; bias negative on money-centers with high fixed-rate
  securities books. Coverage + protection is the playbook.
- NCO trends rolling up *and* CRL (consumer-real-estate-loan) book
  w. low LTV (CRE at peak) ⇒ banking cycle is past peak.
- Office CRE concentration > 4× Tier-1 capital ⇒ shell-shocked for
  any name with non-trivial office book (USB / PNC / WFC).
- Stress loss predicted > 8% capital + CET1 < 10.5% post-stress ⇒
  buyback pause; bias negative on capital-per-share.
- SIV-style repo dislocation (any quarter with quarter-end SOR
  rates > SOFR + 50 bps for more than 2 weeks) ⇒ SCHW-class names
  are exposed to fast deposit-sortie.

## Common biases to watch for

- **EPS-mirroring bias**: the headline financial-press read is "EPS
  beat/miss." Bank EPS is *always* beat-able via ACL release. Read
  pre-provision pre-release, not headline.
- **Theo's-NII fetish**: every analyst publishes an NII guide for
  every bank every quarter. JPM's is canonical (Jamie says it every
  Jan). It is a guide, not a check. Read Q1 actual vs the guide more
  carefully than the guide itself.
- **CRE over-attribution**: regional bank weakness is attributed to
  CRE every quarter regardless of mix. Anchor in the 9-C CRE/Office
  concentration lines, not in the sector-wide narrative.
- **Stress-test-result over-reading**: CCAR pass ≠ buyback-healthy.
  Read the post-stress CET1 (the figure in the Fed's released
  results) + the bank's *ex-ante* stated buyback plan.
- **"Banking is Safer Now" post-hoc narration**: after the 2023
  regional scare, every regional bank deck asserted a "safer now"
  thesis. The bank that said it was safer before the 2023 scare is
  also the one saying it now. Read the data; don't inherit the
  narrative.

## What "good" looks like vs the typical sell-side model

| Metric | Sell-side default | Pack would prefer |
|--------|-------------------|-------------------|
| NIM | Reported NIM y/y | Forward NII guide -vs- actual, with deposit beta implicit |
| Loan loss provision | Reported ACL release as "good" | NCO vs pre-provision pre-release trend |
| Capital adequacy | Basel III CET1 | Holdco CET1 post-stress (latest CCAR / DFAST) |
| EPS growth | Reported EPS | Pre-provision pre-release diluted EPS |
| Multiples | Price-to-book × 1.5× | Book value post-stress; price-to-adjusted-book |

## What an attacker would say about this pack

- "You assert NIM is the master variable, but deposit-betavariability
  is what's driving the cycle. Your pack disciplines on the slope
  (2s10s) but not on the deposit-beta derivative, which is where
  regionals suffered in 2023. Pull deposit-beta into the rubric."
- "CCAR / DFAST are *annual* checks. By the time a bank is being
  tested publicly, the cycle has already turned. Your pack treats
  the stress test as the constraint, not as a check; consider it as
  a *minimum* spare capital requirement, not the actual stress
  reading."
- "The big-deal weight on form 8-K consent-order updates misses
  supervisory letters. The latter comes *before* consent orders and
  is the regulator's quiet warning. Your pack reads the regulator
  by the timestamp file — read it by the document type."
- "Sponsor-loan pipeline as positive trigger is good but only for
  one segment. Retail (consumer loans) demand pulse is a separate
  segment's read. Pack conflates."

## Pack failure modes

- The name is a credit union or community bank (out of scope — not
  in v1 tickers; would need a regional/community pack overlay).
- Operating environment has zero rate cycle (pegged currency, fixed-
  rate regime, etc.) — irrelevant outside the US/EU/UK/JP.
- The cycle is already deep in a NIM downturn *and* rate cuts have
  cleared ⇒ NIM is the wrong vector; read capital + ALLL coverage
  instead.

## Citations

- Federal Reserve stress test methodology and results
  https://www.federalreserve.gov/supervisionreg/dfast.htm
- FRED H.8 — Commercial bank credit
  https://fred.stlouisfed.org/series/H8B1020NCBCMG
- FRED H.15 — Selected interest rates (2s10s reading)
  https://fred.stlouisfed.org/release/h15/
- FDIC Quarterly Banking Profile
  https://www.fdic.gov/quarterly-bank-profile
- SEC EDGAR consolidated financials
  https://www.sec.gov/cgi-bin/browse-edgar
- Each bank investor-day deck (specific URL in citations_used)

---

_pack v2026-08-20 · opinionated analyst framing; not financial advice_
