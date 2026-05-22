# 🔍 Improve Specview BullshitBench Score — Analysis

## The Problem
Specview's anonymous analysis pipeline scores 74.2% on BullshitBench v2, losing ~15 points versus raw Opus 4.6 (89.7%). The structured template forces the model into "helpful analyst" mode, suppressing its natural nonsense-detection. Two techniques (specificity_trap at 0.25, plausible_nonexistent_framework at 1.06) and two domains (finance at 1.20, legal at 1.29) account for most of the gap.

## Hard Constraints
- Model stays Opus 4.6 via `adapter.rewrite()` — no model change, no context injection
- Structured output sections (Problem, Hard Constraints, Open Questions, Dependencies, Out of Scope) are non-negotiable
- Single-pass only — no verification chain, no second LLM call
- Anonymous path — no builder context, no project-specific knowledge available
- Changes must not degrade quality on legitimate braindumps

## Open Questions
- **Where does the skepticism instruction live?** System prompt preamble vs. per-section guidance embedded in the template vs. both. Per-section is more targeted but bloats the template.
- **What's the target score?** Closing all 15 points is unrealistic single-pass. Is 82-85% (top 10) the goal, or just flipping the 9 partial-pushback cases to full (~80%)?
- **Should "Open Questions" be the designated pushback zone, or do we add an explicit "Unverified Claims" section?** A new section is a format change the constraint says to avoid; overloading Open Questions muddies its purpose.
- **Do we treat specificity_trap differently from plausible_nonexistent_framework?** The former requires doubting *numbers*; the latter requires doubting *names*. The prompt fix is different for each — one says "question unsourced metrics," the other says "flag unfamiliar methodologies."

## Dependencies & Sequencing
- System prompt wording must be finalized before template changes — the template amplifies or dampens whatever posture the system prompt sets
- Need a holdout split of BullshitBench questions before any tuning, or we overfit to the benchmark
- Finance/legal weakness may resolve automatically if specificity_trap and framework detection improve — measure before adding domain-specific mitigations
- The 9 partial-score cases should be analyzed first — they reveal the exact phrasing threshold where pushback dies, which informs prompt wording

## Explicitly Out of Scope
- **Multi-pass verification or chain-of-thought pre-check** — violates single-pass constraint; revisit only if prompt-only changes plateau below 80%
- **Domain-specific system prompts or routing** — adds branching complexity for marginal gain; revisit if finance/legal stay weak after generic fixes
- **Authenticated pipeline changes** — that path has builder context and different tradeoffs; separate analysis if needed
- **Changing the scoring rubric or contesting BullshitBench methodology** — the benchmark is the benchmark
- **Training or fine-tuning** — not a lever we control