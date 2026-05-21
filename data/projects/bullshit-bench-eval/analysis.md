# 🔍 BullshitBench Eval — Analysis

## The Problem
Specview's anonymous analysis pipeline anecdotally catches nonsensical input, but there's no structured proof. BullshitBench provides 100 scored questions across 5 domains specifically designed to test this. Formalizing the eval gives publishable metrics and a repeatable regression suite.

## Hard Constraints
- Eval target is the **public anonymous analysis** — `adapter.rewrite()` with haiku, no builder context
- `CHAIN_PROVIDER=cli` — subprocess-based, sequential, 3600s timeout per call
- Runs inside existing Docker container via `docker exec` — no image rebuild
- Questions vendored as `fixtures/questions.v2.json` — pinned, no runtime fetching
- Single Sonnet judge — not reproducing the 3-judge panel

## Open Questions
- **The 71.6s contradiction**: Manual test took 71.6s. At 100 questions sequential, that's ~120 min, not 30-50 min. Either (a) the manual test used a heavier model/longer prompt than the eval will, (b) you're assuming parallelism the CLI provider doesn't support, or (c) the estimate is wrong. Which is it?
- **"No principles injection" vs. the manual test**: The manual test "applied the user's own no-speculative-abstractions principle." If anonymous analysis truly strips builder context, where did that principle come from — the system prompt itself, or was builder context active during the manual test? The eval will only be valid if it matches what you're claiming to eval.
- **What's the scoring target?** If the blog publishes a single number, is it "% of questions scoring ≥1" (any pushback) or "% scoring 2" (clear pushback)? BullshitBench leaderboard uses mean score / 200. Decide now — it changes whether 60% is a win or a failure.
- **CLI provider → haiku?** `CHAIN_PROVIDER=cli` uses `claude-cli` subprocess. Does that actually route to haiku, or whatever model the CLI defaults to? If it's not haiku, you're not evaluating what you think you are.

## Dependencies & Sequencing
- Must confirm which model `CHAIN_PROVIDER=cli` actually invokes before any runs mean anything
- `questions.v2.json` must be vendored before `--dry-run` works — need to pull from petergpt/bullshit-benchmark and confirm v2 schema matches expected format
- Judge prompt design blocks scoring — the 0/1/2 rubric and "known nonsensical element" per question must come from the benchmark data or be authored manually
- Blog post blocks on having a story worth telling — if the score is mediocre, the narrative pivots from "look how good we are" to "here's what we learned"

## Explicitly Out of Scope
- **Reproducing the full 3-judge panel** — not needed for a blog post; re-scope if submitting to the actual leaderboard
- **Comparing against other tools** — the eval proves Specview works, not that it beats ChatGPT; re-scope if competitors respond
- **Modifying the analysis pipeline to improve scores** — this is a measurement, not an optimization pass; re-scope after results are in
- **Builder-context or principles-injected variants** — test the public anonymous path only; a "with context" comparison is a separate eval
- **CI integration** — this is a one-shot benchmark for content, not a regression gate; re-scope if you want to track drift across deploys