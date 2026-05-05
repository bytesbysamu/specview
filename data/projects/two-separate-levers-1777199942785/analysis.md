# 🔍 Two separate levers — Analysis

## The Problem
The CLI adapter hard-caps subprocess execution at 600s; generation tasks exceeding this silently fail and leave implementation guides missing with no recovery path. The frontend already has a polling client, but no backend endpoint exists for on-demand single-task generation, so missing guides can only be recovered by re-running the full bootstrap.

## Hard Constraints
- Option A is a prerequisite for Option B — the background thread calls the same subprocess path with the same cap
- The Angular polling client contract and `implementation_guide/prompts.py` prompt builder already exist; the new endpoint must conform to both
- No direct push to `master` — both changes ship via PR

## Open Questions
- What is the correct timeout ceiling? (hardcode 1200 / env-var override / per-task heuristic based on observed variance)
- Does the generate-task endpoint coexist with bootstrap generation or eventually replace it? (coexist indefinitely / step 4 migrates bootstrap soon / bootstrap is removed once endpoint is stable)
- What must `/status` return — thread state only, or current task name and progress detail? (minimal state / task-aware state / streaming events)

## Dependencies & Sequencing
- Timeout fix must land and be verified before the endpoint ships; otherwise the endpoint inherits the same failure mode
- The endpoint must be validated end-to-end before the frontend button is wired
- Step 4 (bootstrap migration) cannot begin until the endpoint has proven reliability in production

## Explicitly Out of Scope
- **Step 4 (bootstrap refactor)** — marked optional in the brain dump; defer until a second consumer of the endpoint exists
- **Configurable timeout** — no second consumer yet; hardcoding 1200 is sufficient; revisit when task variance data exists
- **Bulk/batch generation** — speculative; no current consumer implies it