# 🎯 Epic: weekly-life-os-1779265846

## Business Value

Specview's spec pipeline turns messy braindumps into structured, actionable output — but today it only proves that for software engineering. Every line of marketing, every positioning conversation, every pricing decision is constrained by that single vertical. If the same analysis → epic → architecture → implementation guide pipeline produces equally sharp output for "friendship investment strategy" or "fitness trend review," Specview stops being a dev tool and becomes a **general-purpose thinking tool**. That is a category shift — from competing with Linear and Notion (crowded, commoditized) to competing with nobody, because structured-thinking-as-a-service has no incumbent.

The weekly life OS braindump is the proving ground, not the product. The real deliverable is evidence: can a non-engineering braindump enter the Specview pipeline and produce output that is as concrete, sequenced, and actionable as a software implementation guide? If yes, every future braindump — career planning, relationship strategy, relocation logistics, financial restructuring — becomes a Specview use case. The addressable market expands from "solo devs who write specs" to "anyone who thinks in messy paragraphs and needs structured plans."

The secondary value is personal: Sam gets a weekly operating system that actually runs, built on infrastructure he already maintains (Flask :3101, Angular :4201, Telegram delivery). But this is a side effect. The primary business outcome is validated generalization of the Specview pipeline.

## Scope

### What This Epic Covers

- **Non-engineering output templates** — New spec templates that make sense outside software (no "architecture.md" for a friendship strategy; instead: analysis → action plan → review criteria)
- **Single-domain POC: Social/People tracking** — Prove the pipeline works on one life domain using existing data (memory files, diary entries, calendar). "You haven't seen Alex in 3 weeks" is the canonical testable output
- **Braindump-in, structured-plan-out for life domains** — User pastes a messy life paragraph into Specview, pipeline produces a structured weekly action plan. No auto-ingestion, no data source polling — manual input, structured output
- **Telegram delivery of weekly output** — Formatted summary pushed via Telegram webhook, under 4096 chars, on a cron schedule
- **Pipeline validation metric** — A concrete rubric to evaluate whether non-engineering output meets the same quality bar as software specs

### What This Epic Does NOT Cover

- ❌ **Multi-source data dashboard (fitness, finance, GitHub, calendar visualizations)** — That is a full product. Re-scope only after the single-domain pipeline works end-to-end
- ❌ **Automated data ingestion (Google Calendar API, Strava, Apple Health, bank statements)** — Data adapters are independent work gated on a decision this epic intentionally avoids: auto-ingest vs. manual paste. Manual paste is the MVP
- ❌ **Friend relationship scoring algorithm** — Application logic on top of the pipeline, not proof of generalization. Re-scope after POC validates
- ❌ **Daily morning/evening check-ins** — Weekly is the atomic unit. Daily cadence adds operational burden that will kill adoption within 2 weeks for a solo dev
- ❌ **Monthly review cadence** — Monthly is "run weekly 4x and summarize." Don't build it separately
- ❌ **Voice note transcription** — Another integration layer. Text input first
- ❌ **OpenClaw / ClawBoi dependency** — Scheduled triggers are cron. Intelligence comes from the Specview pipeline. No VPS agent runtime required

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Define non-engineering output templates** | None | — | 1 day | High |
| 2 | **Extend Specview pipeline to accept life-domain braindumps** | Task 1 | — | 2 days | High |
| 3 | **Build social/people domain POC end-to-end** | Task 2 | — | 2 days | High |
| 4 | **Wire Telegram delivery for weekly output** | Task 3 | Yes (with Task 5) | 1 day | High |
| 5 | **Validate generalization with quality rubric** | Task 3 | Yes (with Task 4) | 0.5 days | Low |

**Task 1 — Define non-engineering output templates.** The current pipeline emits software-shaped documents (epic, architecture, implementation guide). A "friendship investment strategy" braindump needs different output sections: situation analysis, action items with owners and deadlines, review triggers, success criteria. Design 1–2 reusable templates that work across life domains. Deliverable: template files checked into the Specview repo, validated against 2–3 sample braindumps on paper before any code runs.

**Task 2 — Extend Specview pipeline to accept life-domain braindumps.** The pipeline currently assumes engineering context (code references, API contracts, deploy targets). Modify the chain adapter's prompt construction so it detects domain type from the braindump content and selects the appropriate output template from Task 1. No new routes — the existing braindump ingestion endpoint handles this. Deliverable: a life-domain braindump pasted into Specview produces structured output using the new templates.

**Task 3 — Build social/people domain POC end-to-end.** Take a real braindump — "I feel like I haven't seen my close friends enough, I keep canceling plans, Alex and I used to hang out weekly but it's been a month" — and run it through the extended pipeline. The output should name specific people, suggest concrete actions with timeframes, and flag relationship gaps. Use existing memory file data (people tracker, diary entries) as context fed into the braindump manually. Deliverable: one complete life-domain spec that Sam would actually act on.

**Task 4 — Wire Telegram delivery for weekly output.** Simple webhook: cron fires weekly (Sunday 18:00), calls Specview's pipeline with a pre-composed braindump prompt (or the most recent manual one), formats the output for Telegram (≤4096 chars), and sends via bot API. No OpenClaw. Deliverable: Sam receives a formatted weekly social pulse on Telegram every Sunday evening.

**Task 5 — Validate generalization with quality rubric.** Define 5 concrete criteria (e.g., "output contains ≥3 named action items with deadlines," "output references specific people/data from context," "a stranger could execute the plan without asking clarifying questions"). Score the POC output against this rubric. Deliverable: a pass/fail verdict on whether Specview generalizes, with specific evidence.

## Success Criteria

- ✅ A non-engineering braindump entered into Specview produces a structured action plan using life-domain templates (not software-shaped output)
- ✅ The social/people POC output names specific people, concrete actions, and timeframes — equivalent in specificity to a software implementation guide
- ✅ Weekly Telegram delivery fires autonomously via cron with zero manual intervention after setup
- ✅ Telegram message stays under 4096 characters and is readable without a web dashboard
- ✅ Quality rubric scores the POC output as actionable by an independent reader (not just the author)

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking