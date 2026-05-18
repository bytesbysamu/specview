---
name: Swiss finance B2B SaaS competitive landscape (researched 2026-04)
description: What incumbents already exist for Swiss EAM/wealth-tech, where the wedge opportunities are, and key reference founders
type: project
---

## Saturated spaces — DO NOT enter head-on

After two rounds of verification on 2026-04-11, the following Swiss B2B finance verticals are confirmed saturated. Head-on platform plays here are a trap:

**EAM / wealth management platforms:**
- **WealthArc** — venture-funded; ~90% Swiss custodian coverage
- **Finup.ch** — mobile-first, Swiss insider founder
- **GWAP Financial** — FINMA-regulated, CFA-led
- **Expersoft, Etops, Assetmax, Allocare, Indyon** — established Swiss wealth-tech

**General Swiss Treuhand / SME accounting software:**
- **Bexio** — dominant cloud accounting/Treuhand for Swiss SMEs
- **Abacus / AbaWeb** — established enterprise + SME
- **Klara** — popular Swiss cloud accounting
- **Swiss21** — Bexio competitor
- **Banana Buchhaltung** — cheap alternative
- **Tresio** — another contender
- Comparison ecosystem at treuhand-suche.ch publishes yearly shootouts; every Swiss Treuhandbüro already uses one of these

**Crypto fund NAV/accounting (high end):**
- **Lukka** — has Bitcoin Suisse as a customer; dominant US-based enterprise crypto fund accounting
- **Cryptio, Coinfirm** — adjacent enterprise players
- Possible exception: very small Zug crypto funds (<$50M AUM) likely still on Excel and can't afford Lukka — but this bets against Lukka moving down-market

**Family office software:** Aleta, Masttro and others are already there.

## The most promising wedge identified: FINIA compliance toolkit

FINIA created a **new regulated category** for Swiss portfolio managers AND trustees in 2020; transition period expired 2023; all licensed firms now mandatorily compliant. The compliance workflows are **narrow, painful, and not addressed by general Treuhand software (Bexio/Abacus) or wealth platforms (WealthArc/Etops)** — those are bookkeeping or portfolio tools, not compliance tools. The compliance niche is too narrow for the big incumbents to bother building.

**Target workflows (verified pain):**
- Suitability checks per client (currently in Word/Excel)
- Conflict of interest register
- KYC/AML for trust beneficiaries
- FATF beneficial-ownership reporting
- FINMA audit trail / Sorgfaltspflichten log
- Periodic risk-classification review
- Annual compliance report

**TAM (revised):**
- FINIA-licensed trustees in CH: ~250–300 firms (NOT the ~600 figure I initially gave Sam — verify against current FINMA register)
- FINIA-licensed portfolio managers: ~1,700 firms
- Combined: ~2,000 firms facing the same compliance regime
- At €299/mo: pessimistic 1% capture = €6k MRR; realistic 3% = €18k MRR
- **Small enough that VC-backed competitors won't bother; large enough for real side income — the textbook micro-SaaS sweet spot for Sam**

**Competitor verification completed 2026-04-11 via WebFetch:**

- **Aviolo Compliance Solutions GmbH** — **pure consultancy**, NOT a SaaS competitor. Founded 2016, 2 founders (Brent Vanderbrook, Susi Maron), sales-driven "contact us" model. Offers full-service outsourcing, co-sourcing, advisory. No platform, no self-service. Serves asset managers, trust companies, fund managers, family offices under SEC/FinSA/FinIA. **Verdict: no product overlap.**

- **SwissComply** — **hybrid: consulting firm with lightweight software bolt-on.** Main offering is "personal risk & compliance officer" (outsourcing/body lending). Has a product called **Online-ICS** — but this is **firm-level Internal Control System (ICS) governance**, NOT client-level compliance workflows. Features: risk control function, dashboard with reminders, Swiss data centers, pre-built "Standard Risk & Control Set". No self-service signup, no demo, "contact us" only. **Verdict: adjacent but not direct — operates at a different layer of compliance than the wedge we're pursuing.**

**CRITICAL INSIGHT — the wedge is confirmed open:** The distinction between firm-level ICS (SwissComply's domain) and client-level compliance workflows (suitability checks, per-client audit trails, conflict of interest per relationship, KYC per beneficiary) is important. Nobody is doing client-level per-interaction compliance as focused self-serve SaaS. Law firms consult on it, SwissComply outsources it with humans, Aviolo consults on it — but no product exists. **That's the wedge.**

**FINMA register downloaded and analyzed (2026-04-11):**
- Two Excel files at `finma.ch/en/authorisation/portfolio-managers-and-trustees/`:
  - **vvtr.xlsx** (main list, SO-supervised): **1,486 firms total** — 1,344 portfolio managers, 152 trustees, 11 both
  - **grfinig.xlsx** (small list, FINMA-supervised group companies): ~100 firms, mostly big-firm subsidiaries — less interesting as prospect list
- **Columns in vvtr.xlsx:** `Name | City | Portfolio Manager (X) | Trustee (X) | Supervisory Organisation` — **NO emails, websites, phone, or license dates**. Enrichment required from firm websites.
- Files cached locally at `/tmp/finma/vvtr.xlsx` and `/tmp/finma/grfinig.xlsx` for the current session (ephemeral — will need re-download in future sessions).

**Top cities by firm count (important — changes primary target):**
- **Genève: 369** 🇫🇷 (French — LARGEST EAM hub, bigger than Zurich)
- **Zürich: 361** 🇩🇪
- Lugano: 115 🇮🇹
- Zug: 83 🇩🇪
- Basel: 40 🇩🇪
- Lausanne: 31 🇫🇷
- Baar: 21 🇩🇪, Wollerau: 16 🇩🇪, Nyon: 16 🇫🇷

**Addressable market with Sam's DE+FR fluency:**
- German-speaking zones: ~550 firms (37% of market)
- French-speaking zones: ~420 firms (28% of market)
- **Combined reachable: ~970 firms (65% of Swiss FINIA market)**
- This is Sam's language moat, quantified. EN-only competitors are effectively locked out.

**CRITICAL TARGETING CORRECTION:** Earlier recommendation to primarily target trustees was wrong. Only 152 trustees exist — TAM too small for a side project. **Primary target is now PORTFOLIO MANAGERS (1,344 firms).** Same FINIA compliance regime (FinSA Art. 11 applies identically), 9x larger market. Trustees become a secondary segment.

**Geneva (French) is the #1 EAM hub in Switzerland** (369 firms vs Zurich's 361). Sam's French fluency is not a nice-to-have but a critical competitive advantage. Consider French-first outreach even before German.

**Chosen MVP wedge: Suitability Check Logger (Geeignetheitsprüfung / FinSA Art. 10–14).** Single workflow: form-based client-level suitability assessment with full audit trail and PDF export for FINMA audit prep. Pricing tiers CHF 99 / 299 / 599 per month. MVP scope deliberately narrow — no portfolio integration, no custodian APIs, no firm-level ICS. Upsell path: expand later to conflict register, AML/KYC, annual audit prep.

**Pre-launch risks:**
- FinSA Art. 11 has legally prescribed wording — budget ~CHF 500 for a Swiss compliance lawyer review of the workflow before first sale
- Swiss B2B sales cycles run 4–8 weeks even at CHF 99/mo; don't panic on silent week 2
- Prospect list prep may take 2 hours if register lacks emails (website scraping fallback)

## Free prospect list: FINMA public register

The FINMA register of licensed portfolio managers and trustees is **public and downloadable**. URL pattern: `finma.ch/en/authorisation/portfolio-managers-and-trustees/`. Look for the "FLV ERVT" download. This is the entire prospect universe of FINIA-licensed Swiss firms, free, no scraping needed. Whether the download includes contact emails or just firm names is still unverified — Sam should download and check.

## Free prospect list: FINMA public register

The FINMA register of licensed portfolio managers and trustees is **public and downloadable** as a CSV/PDF. URL pattern: `finma.ch/en/authorisation/portfolio-managers-and-trustees/`. Look for the "FLV ERVT" download — this is the entire prospect universe of FINIA-licensed Swiss firms, free, no scraping needed. Massive structural advantage for cold outreach.

## Reference case studies to learn from

- **Parqet** — €108k MRR, bootstrapped, DACH-only fintech for retail investors. Founder had NO finance background. Strongest proof point that DACH bootstrapping works at scale. Note: B2C, not B2B.
- **Aumico** — Excel→PDF financial statements for Swiss accounting firms; 4k recurring licenses in 2 years. Bootstrapped via iterative prototypes. Closer to the "wedge tool" model.
- **einzly.ch** — CHF 9/mo accounting SaaS for Swiss self-employed, solo bootstrapped. Low ticket but proves the model.

## DACH solo-founder community (Sam's peers)

- **happy-bootstrapping.com** — German-language podcast specifically about DACH bootstrappers; should be subscribed
- **Jannis Kuhrt (kcalculator.de)** — B2B SaaS alongside full-time job + family. Closest profile match to Sam.
- **Lukas Hermann (Stagetimer)** — €20k MRR
- **Andreas Schwarzinger** — Swiss student platform founder
- **Moritz Dausinger** — Mailparser/Docparser, eventually sold to Sureswift

**How to apply:** When recommending niches for Sam, default to wedge/sub-workflow plays or under-served adjacent verticals (trustees, crypto funds), NOT head-on platform competition with WealthArc/Finup/Etops. Reference Parqet for DACH bootstrapping benchmarks. Always check if a competitor exists before recommending — verify this snapshot since the market moves fast.
