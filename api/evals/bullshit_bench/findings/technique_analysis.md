# Technique Analysis — BullshitBench v2 Baseline Failures

Baseline: 74.2% leaderboard score, 21 accepted (score 0), 9 partial (score 1), 69 rejected (score 2).

## Techniques by failure rate

### specificity_trap — 0.25 mean (7/8 accepted, 1/8 rejected)

The pipeline's worst technique by far. Questions embed fabricated but hyper-specific numbers (percentages, thresholds, latencies) presented as domain facts. The pipeline absorbs these into Hard Constraints or The Problem section as given context. Specific numbers *feel* like measurements, not claims — the pipeline has no mechanism to distinguish "our p99 is 340ms" (user measurement, legitimate) from "the Henderson threshold for cache invalidation is 340ms" (fabricated domain fact).

**Failure pattern:** Fabricated specifics land in Hard Constraints as fixed requirements. The model never questions whether the number is real because the analysis template says Hard Constraints = "Decisions already made."

### plausible_nonexistent_framework — 1.06 mean (8/16 accepted, 8/16 rejected)

Fabricated methodologies with real-sounding names (e.g., "differential indemnity decomposition", "Henderson-Kraft protocol"). Success rate is ~50/50 — the model catches some when the name sounds novel enough but misses when the framework name follows real naming conventions. Caught frameworks tend to be in the software domain where the model has stronger training coverage. Missed frameworks tend to be in finance/legal where domain jargon is inherently opaque.

**Failure pattern:** Named frameworks land in Dependencies or Hard Constraints as assumed tooling. The model treats proper nouns as established concepts and builds analysis around them.

### cross_domain_stitching — 1.2 mean (1/5 rejected, 4/5 partial or accepted)

Questions graft a concept from one domain onto another (e.g., applying physics concepts to software). The pipeline sometimes notices the mismatch but still engages substantively — producing a score of 1 (partial) rather than outright rejection.

**Failure pattern:** The model senses something is unusual but routes its discomfort into Open Questions as "this approach is unconventional" rather than rejecting the premise.

### temporal_category_error — 1.2 mean (3/5 scored, some accepted)

Questions apply time-dependent reasoning incorrectly. The pipeline treats temporal claims as factual context.

### sunk_cost_framing — 1.43 mean (mixed)

Questions use sunk cost reasoning to justify continued investment. The pipeline sometimes catches the logical fallacy but often restructures it as a legitimate constraint.

### confident_extrapolation — 1.5 mean (2/4 rejected)

Questions extrapolate trends beyond their valid range. The pipeline catches obvious overreach but misses subtle extrapolations.

## Techniques the pipeline catches well

- **authoritative_framing** (2.0): Claims backed by fake authority figures. The pipeline flags these in Open Questions.
- **reified_metaphor** (2.0): Metaphors treated as literal mechanisms. Easy for the model to detect.
- **wrong_unit_of_analysis** (2.0): Wrong measurement level applied. Clear conceptual mismatch.
- **misapplied_mechanism** (1.85): Real mechanism applied to wrong domain. The pipeline excels at "this doesn't apply here."
- **fabricated_authority** (1.82): Made-up standards or certifications. The pipeline questions unfamiliar authorities.
- **nested_nonsense** (1.71): Multiple layers of nonsense. More nonsense = more chances to catch it.

## Domain patterns

- **Physics** (1.73) — strongest. Scientific nonsense is easiest for the model to detect.
- **Software** (1.55) — good. Strong training coverage, catches most techniques.
- **Medical** (1.53) — decent. Medical jargon is somewhat opaque but mechanisms are catchable.
- **Legal** (1.29) — weak. Legal jargon creates authority the model doesn't question.
- **Finance** (1.20) — weakest. Financial specifics and frameworks are hardest to verify.

## Key insight

The two failing techniques share a root cause: **the pipeline lacks a distinction between user claims and domain assertions**. When a braindump says "we measured X" that's the user's data — analyze it. When it says "the industry standard is X" or "use the Henderson protocol" — that's a domain claim that should be verified. The current template treats both identically as input context.
