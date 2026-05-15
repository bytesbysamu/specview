# 🔍 SpecView — Analysis

## The Problem
Developers (especially solo founders) work in brain dumps — messy voice notes, chat logs, scattered markdown — but ship from structured specs. Today the gap is manual: you either write specs by hand (slow, skipped) or let AI chat generate walls of text with no enforced structure. SpecView turns a brain dump into a linked spec set (analysis → epic → architecture → timeline) with AI generation and coherence linting, so one person can maintain real documentation without the overhead.

## Hard Constraints
- **Launch: Sunday 2026-05-18** — days away, scope is frozen
- **Stack locked**: Flask :3101 + Angular :4201, already running
- **Solo operator**: no editorial team, no onboarding staff — the product must self-explain
- **Existing users**: at least two accounts (Sam + a test account) with real project data in production storage

## Open Questions
- **What is the launch surface?** Product Hunt? Twitter thread? Landing page? A `/` route that explains SpecView to strangers doesn't exist in the current frontend — is one needed by Sunday, or is launch just "share the URL"?
- **Who is the launch audience?** Solo devs like Sam? Dev teams? AI-tool enthusiasts? This decides the pitch angle (productivity tool vs. AI writing tool vs. dev methodology)
- **What's the pricing posture at launch?** Free? Free tier + paid? The billing module exists but its state is unclear — is it wired up or stubbed?
- **"Boilerplate doc page" inspiration** — the brain dump references a purchased boilerplate's docs as the origin. Is this the positioning? ("Documentation pages for your project, generated from brain dumps") Or has the product evolved past that?
- **Historical "constellation" projects** — referenced as proof the product works over time, but they don't exist in the codebase or mock data. Are they in a production data directory, lost, or aspirational?

## Dependencies & Sequencing
- **Product description blocks launch** — you can't share SpecView without a one-liner and a 30-second explanation. This is the actual blocker, not features.
- **Dogfooding is both proof and risk** — using SpecView to write SpecView's own spec is a great demo, but if the output is incoherent, it undermines the pitch. The coherence linter should pass on SpecView's own project before Sunday.
- **Second account testing blocks launch confidence** — the test account flow (signup → first project → first generation) is the real onboarding path. Any friction there is launch-blocking.

## Explicitly Out of Scope
- **New features before Sunday** — launch is a messaging event, not a feature event. No new endpoints, no new AI actions. Revisit after launch metrics exist.
- **Multi-user collaboration** — mentioned nowhere in the brain dump but could creep in. SpecView is single-player for now. Trigger: paying user requests it.
- **Migration of "constellation" era docs** — interesting for storytelling but not launch-blocking. Trigger: if you want a "look how this evolved" demo video.
- **Spec evolution tracking as a feature** — the brain dump hints at "track all the spec evolution." Git history already stores this. Don't build a UI for it pre-launch. Trigger: user feedback says history browsing matters.