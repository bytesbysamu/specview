# 🔍 weekly-life-os-1779265846 — Analysis

## The Problem
Specview's spec pipeline turns messy software braindumps into structured, actionable output — but only for engineering domains. There is no evidence it generalizes. The weekly life OS braindump is the test case: if the same pipeline produces equally sharp specs for "friendship investment strategy" or "fitness trend review," Specview becomes a general-purpose thinking tool, not a dev tool. The life OS itself is secondary to proving this generalization.

## Hard Constraints
- No OpenClaw/ClawBoi dependency — scheduled triggers are just cron, intelligence comes from the spec pipeline
- Specview is the core (Flask :3101 + Angular :4201) — this is a feature of Specview, not a new project
- Telegram delivery must stay under 4096 chars per message
- Solo dev — if it requires daily manual input to function, it will die within 2 weeks
- No Redis, no Postgres, no external queue

## Open Questions
- **What does "Specview processes a life braindump" actually mean mechanically?** Does the user paste "I feel stuck on fitness and haven't seen friends" and get a structured weekly plan? Or does Specview ingest data sources and auto-generate the braindump? These are completely different products.
- **Which life domain is the single POC domain?** The braindump lists health, social, career, finances, side projects. Pick ONE to prove generalization — which one? (Suggest: social/people tracking — it's novel, has existing data in memory files, and "you haven't seen Alex in 3 weeks" is a concrete, testable output.)
- **What is the success metric for "Specview generalizes"?** Is it "the pipeline runs without errors on non-code input" or "the output is as actionable as a software implementation guide"? Without this, you'll ship something and not know if it worked.
- **Cron where?** The VPS that ran OpenClaw? The Coolify deploy? A GitHub Action? This is a deployment decision, not an architecture one, but it needs answering before implementation.

## Dependencies & Sequencing
- Proving Specview generalizes is gated on defining what "non-engineering spec output" looks like — the current templates (epic → architecture → implementation guide) are software-shaped. You need new output templates before you can run the pipeline.
- Data adapters (Google Calendar, diary files) are independent of each other but ALL blocked until you decide whether Specview ingests raw data or the user pastes a braindump manually.
- Telegram delivery is independent — it's a webhook, buildable in parallel with anything else.

## Explicitly Out of Scope
- **Multi-source dashboard with fitness/finance/GitHub visualizations** — that's a full product, not a POC. Re-scope when the single-domain pipeline works end-to-end.
- **Friend relationship scoring algorithm** — interesting feature, but it's application logic on top of the pipeline, not proof of generalization. Re-scope after POC validates.
- **Bank statement parsing / financial tracking** — requires PSD2/API integrations or CSV parsing, high effort, low signal for proving the core thesis. Re-scope if finances become the POC domain.
- **Voice note transcription pipeline** — another integration layer. Re-scope after daily check-in cadence is proven with text input.
- **Monthly review cadence** — weekly is the atomic unit. Monthly is just "run it 4x and summarize." Don't build it separately.