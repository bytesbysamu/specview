# 🎯 Epic: Improve Specview BullshitBench Score

## Business Value

Specview's anonymous analysis pipeline currently scores 74.2% on BullshitBench v2, ranking ~17th out of 158 models. Raw Opus 4.6 scores 89.7% (rank 5). The pipeline is making the model *measurably dumber* at detecting nonsense — a 15-point regression caused entirely by the product layer. Every braindump containing fabricated metrics, invented frameworks, or authoritative-sounding jargon gets laundered into clean, structured analysis that looks credible. Users who trust that output make decisions on fiction.

This is a product credibility problem, not an academic benchmark exercise. Specview's core value proposition is turning messy braindumps into reliable analysis. If the pipeline uncritically accepts "the Henderson-Kraft protocol" or a fabricated "340ms p99 regression" and builds structured plans around them, the output is worse than useless — it's confidently wrong. Users don't come back after acting on analysis that turned out to be built on nonsense. The 21.2% full-acceptance rate means roughly one in five adversarial inputs sails through completely unchallenged.

Closing the full 15-point gap in a single-pass pipeline is unrealistic, but recovering 8–10 points (target: 82–85%) would move Specview from mid-pack to top-10 territory on a benchmark that AI-literate buyers actually check. The fix is entirely in prompt engineering — no model change, no infrastructure, no second LLM call — making this high-leverage work with near-zero operational cost.

## Scope

### What This Epic Covers

- **Holdout evaluation framework** — split BullshitBench into tuning and validation sets so prompt changes are measured, not overfit
- **Partial-score case analysis** — extract the exact phrasing patterns where pushback weakens, informing prompt wording for the two weakest techniques
- **System prompt skepticism calibration** — add a skepticism posture to the system prompt that activates on unsourced claims without suppressing helpful analysis of legitimate input
- **Template-level claim channeling** — modify the analysis template so unsourced specifics and unfamiliar frameworks surface in Open Questions rather than being absorbed as Hard Constraints or Dependencies
- **Regression validation** — confirm improvements on the holdout set and verify no degradation on legitimate braindumps

### What This Epic Does NOT Cover

- ❌ **Multi-pass verification or chain-of-thought pre-check** — violates the single-pass constraint; revisit only if prompt-only changes plateau below 80%
- ❌ **Domain-specific system prompts or routing** — finance/legal weakness may resolve with generic technique fixes; measure before adding branching complexity
- ❌ **Authenticated pipeline changes** — that path has builder context and different tradeoffs; separate epic if needed
- ❌ **Changing the BullshitBench scoring rubric** — the benchmark is the benchmark
- ❌ **Model change or fine-tuning** — Opus 4.6 via `adapter.rewrite()` is fixed; not a lever we control

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Create holdout evaluation split** — partition BullshitBench v2 into 60/40 tuning/holdout sets, stratified by technique and domain, plus a set of 10–15 legitimate braindumps for regression testing | None | With T2 | 0.5 days | High |
| 2 | **Analyze partial-score and full-miss cases** — examine the 9 partial-pushback responses and 21 full-acceptance responses to extract the exact phrasing thresholds, input patterns, and section placement where skepticism dies, grouped by technique (specificity_trap vs. plausible_nonexistent_framework) | None | With T1 | 1 day | High |
| 3 | **Revise system prompt with calibrated skepticism** — add skepticism posture to the system prompt preamble targeting unsourced metrics, fabricated-sounding named methodologies, and domain jargon without established precedent; posture must not trigger on legitimate braindump content | T2 | — | 1 day | High |
| 4 | **Update analysis template claim channeling** — modify template instructions so the model routes unverifiable claims (specific numbers without source, unfamiliar named frameworks) into Open Questions as "unverified" rather than absorbing them into Hard Constraints or Dependencies | T3 | — | 1 day | High |
| 5 | **Validate against holdout set and regression suite** — run the updated pipeline against the holdout split and legitimate braindump set; confirm score improvement and no quality degradation on real inputs | T1, T4 | — | 0.5 days | High |

## Success Criteria

- ✅ BullshitBench v2 holdout-set score ≥ 82% (up from 74.2% baseline)
- ✅ specificity_trap mean score ≥ 1.0 (up from 0.25) — at least half of fabricated-number questions get pushback
- ✅ plausible_nonexistent_framework mean score ≥ 1.5 (up from 1.06) — majority of fake frameworks flagged
- ✅ Full-acceptance rate (score 0) drops below 12% (down from 21.2%)
- ✅ Legitimate braindump regression suite shows no new false-positive skepticism (0 real inputs flagged as nonsense)
- ✅ No increase in response latency or token cost (single-pass constraint preserved)

## Related Documents

- [Analysis](./analysis.md) — Problems driving this epic
- [Solution Architecture](./architecture.md) — System design
- [Timeline](./timeline.md) — Status tracking