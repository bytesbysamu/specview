# 🎯 Epic: SpecView — Launch-Ready Product Definition

## Business Value

Solo developers and small-team founders generate enormous volumes of unstructured thinking — voice notes, chat logs, scattered markdown, brain dumps — but ship from structured specifications. The gap between raw thinking and shippable documentation is currently filled by either manual spec-writing (which gets skipped under time pressure) or unstructured AI chat output (which produces walls of text with no enforced shape). SpecView closes this gap: paste a brain dump, get a linked spec set (analysis → epic → architecture → timeline) with AI generation and coherence linting. One person maintains real documentation without the overhead of a technical writing process.

The market is every solo founder and indie hacker who knows they *should* document but doesn't because the cost exceeds the perceived benefit. SpecView flips the economics: documentation becomes a byproduct of thinking out loud, not a separate chore. The initial paying audience is developers who already use AI tools (Claude, Cursor, Copilot) and understand that structured context improves AI output — SpecView becomes the structured-context layer for their entire project lifecycle. The boilerplate-documentation-page origin story is the pitch hook: "You know those beautiful docs pages that ship with premium boilerplates? SpecView generates those from your brain dumps."

Launch on Sunday 2026-05-18 is a messaging event. The product runs, users exist, data is real. What's missing is the ability to *explain* SpecView to someone encountering it cold — that explanation is the launch surface, and defining it is the core of this epic.

## Scope

### What This Epic Covers

- **Product positioning and one-liner** — a crisp description of what SpecView is, who it's for, and why it matters, derived from the product's own generated specs (dogfooding as proof)
- **First-visit explanation surface** — whatever a stranger sees when they hit the URL for the first time, giving them a 30-second path from "what is this?" to "let me try it"
- **Dogfood validation** — SpecView's own project spec set must pass coherence linting and read as a credible demo of the product's output quality
- **New-user onboarding path** — the second-account flow (signup → first project → first brain dump → first generated spec) must be frictionless end-to-end
- **Launch distribution plan** — where the URL gets shared, what the accompanying message says, what success looks like in the first 48 hours

### What This Epic Does NOT Cover

- ❌ **New features or endpoints** — launch is messaging, not engineering; feature work resumes after launch metrics exist
- ❌ **Multi-user collaboration** — SpecView is single-player; trigger: a paying user requests shared projects
- ❌ **Migration of historical constellation-era docs** — useful for storytelling but not launch-blocking; trigger: demo video production
- ❌ **Spec evolution tracking UI** — git history already stores this; trigger: user feedback says history browsing matters
- ❌ **Billing and pricing enforcement** — free at launch; pricing posture decided after first usage data

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Define product positioning and one-liner** | None | — | 0.5 days | High |
| 2 | **Validate dogfood spec set (SpecView documenting itself)** | T1 (positioning informs which project specs to showcase) | Can overlap T1 | 1 day | High |
| 3 | **Build first-visit explanation surface** | T1 (needs the one-liner and pitch copy) | — | 1 day | High |
| 4 | **End-to-end new-user onboarding walkthrough** | T3 (explanation surface is the entry point) | — | 0.5 days | High |
| 5 | **Write launch distribution copy and select channels** | T1, T2 (needs positioning and a credible demo) | Can overlap T4 | 0.5 days | Low |

## Success Criteria

- ✅ A stranger can visit the SpecView URL, understand what the product does within 30 seconds, and start a project without external instructions
- ✅ SpecView's own spec set (analysis → epic → architecture → timeline) passes the coherence linter with no critical violations
- ✅ The second-account signup → first-generation flow completes without errors or dead ends
- ✅ A shareable one-liner and 2-sentence pitch exist and are embedded in the product's landing surface
- ✅ At least one distribution channel (Product Hunt, Twitter/X, or direct URL share) has prepared launch copy ready to post Sunday

## Related Documents

- [Analysis](./analysis.md) – Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) – System design and technical decisions
- [Timeline](./timeline.md) – Status tracking and delivery schedule