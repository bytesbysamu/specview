# 🏗️ Solution Architecture: Improve Specview BullshitBench Score

## Architecture Overview

This epic is a prompt engineering intervention, not an infrastructure change. The anonymous analysis pipeline — `adapter.rewrite()` with Opus 4.6, a system prompt, and a structured template — is the entire surface area. The architecture defines where skepticism enters that pipeline, how claims get routed through the existing output sections, and how we measure the effect without overfitting to the benchmark.

The key insight is that the pipeline's two weakest techniques (specificity_trap at 0.25 mean, plausible_nonexistent_framework at 1.06) fail for different reasons that require different interventions at different layers. Fabricated numbers slip through because the template treats specifics as constraints by default — a channeling problem in the template layer. Fabricated frameworks slip through because the system prompt's "helpful analyst" posture suppresses the model's instinct to flag unfamiliar concepts — a calibration problem in the preamble layer. A single "be more skeptical" instruction would address neither precisely and would risk degrading legitimate analysis. The architecture therefore separates the skepticism posture (system prompt preamble) from the claim routing logic (template section instructions), tuning each independently.

The evaluation framework sits outside the pipeline itself but governs every change to it. A stratified holdout split prevents the classic prompt-tuning failure mode: optimizing phrasing until it aces the test set while silently breaking on real inputs. The holdout set is never seen during tuning; the regression suite of legitimate braindumps ensures the skepticism dial doesn't turn so far that the product becomes adversarial toward its own users.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | All pipeline changes flow through `adapter.rewrite()`. No new AI call paths. The system prompt and template are passed as arguments to the existing adapter — no provider-level changes. |
| P4 — No Speculative Abstractions | One skepticism posture for all domains. No finance-specific or legal-specific prompt branches. The two weakest techniques get targeted phrasing, but delivered through a single unified prompt — not a routing layer. |
| P2 — Thin HTTP Layer | No route changes. The anonymous analysis endpoint calls the same service function with the same signature. Prompt content changes are invisible to the HTTP layer. |
| Single-pass constraint | No second verification call, no chain-of-thought pre-check, no self-critique loop. Every improvement must fit within the existing single `adapter.rewrite()` invocation. Token budget and latency stay flat. |
| Measurement before intervention | The holdout split and baseline scoring exist before any prompt change ships. Every tuning iteration is scored against the tuning set only; the holdout set validates the final version exactly once. |

## Component Design

### Holdout Evaluation Framework

**Purpose**: Prevent overfitting prompt changes to BullshitBench while providing fast feedback during tuning iterations.

The 100-question BullshitBench v2 corpus is partitioned into a 60-question tuning set and a 40-question holdout set, stratified by both technique (13 categories) and domain (5 categories). Stratification matters because the weakest techniques have small sample sizes — specificity_trap has only 8 questions total, so a random split could put 7 in one set and 1 in the other, making measurement meaningless. The stratification ensures each set contains a proportional share of every technique-domain combination.

A separate regression suite of 10–15 legitimate braindumps covers the product's real use cases: technical architecture braindumps, product feature descriptions, vague early-stage ideas, and braindumps with real (not fabricated) metrics. These are not BullshitBench questions — they're the control group that catches false-positive skepticism. A legitimate braindump about "implementing Redis cache eviction" should not trigger the same skepticism as a fabricated "Fibonacci-Lehmer cache eviction strategy."

The evaluation framework lives as data files within the project directory, not as pipeline infrastructure. Scoring is manual during tuning (the rubric is simple: 0/1/2 per question) with results tracked in the project's data files. No new endpoints, no new services.

### System Prompt Skepticism Layer

**Purpose**: Restore the model's natural pushback instincts that the current "helpful analyst" posture suppresses, without flipping it into adversarial reviewer mode.

The current system prompt — "You are a markdown spec writer" — establishes an identity that prioritizes structured output over epistemic caution. The model adopts analyst mode and treats all input claims as context to organize, not assertions to evaluate. This is why raw Opus 4.6 scores 89.7% (it freely challenges claims) while the pipeline scores 74.2% (it dutifully analyzes them).

The skepticism layer adds a calibrated posture to the system prompt preamble — positioned after the identity statement but before the template instructions. The posture targets two specific failure patterns without broad-spectrum skepticism:

**Unsourced specifics**: Precise numbers, percentages, thresholds, and metrics presented without attribution or derivation. The posture instructs the model to distinguish between "the user measured X" (legitimate, analyze it) and "X is an established fact about the domain" (unverifiable in a braindump, surface it as a question). This directly addresses the specificity_trap weakness where fabricated numbers like "340ms p99 regression" get absorbed as hard constraints.

**Unfamiliar named methodologies**: Proper-noun frameworks, protocols, or methodologies that the model cannot confirm from training data. The posture instructs the model to note when a named approach is unfamiliar rather than treating it as given context. This addresses the plausible_nonexistent_framework weakness where names like "Henderson-Kraft protocol" get analyzed as if they were real.

The critical calibration constraint: the posture must be conditional, not absolute. Braindumps legitimately contain specific numbers the user measured and niche frameworks the user actually uses. The skepticism triggers on claims presented as universal facts, not on claims presented as the user's own data or chosen tools. This distinction is what separates a helpful skeptic from an adversarial pedant.

### Template Claim Channeling

**Purpose**: Give the model a structural mechanism to express skepticism within the existing output format, so flagged claims land in the right section instead of being swallowed by the wrong one.

The current analysis template defines five output sections: The Problem, Hard Constraints, Open Questions, Dependencies, and Out of Scope. When the model detects something questionable, it needs a place to put it. The partial-score analysis from the baseline shows that successful pushback naturally lands in Open Questions ("needs validation", "no established precedent"). Failed pushback happens when claims get absorbed into Hard Constraints or Dependencies — sections whose semantic frame implies the claim is accepted fact.

The template modification adds channeling instructions to the section definitions themselves — not as a separate skepticism block, but as part of how each section defines what belongs in it. Hard Constraints gets a narrowed admission criteria: only claims the user explicitly states as their own requirements or measurements, not domain assertions the model cannot verify. Open Questions gets an expanded scope: unverifiable specifics and unfamiliar frameworks are explicitly listed as belonging here, with a "flag as unverified" instruction.

This channeling works with the system prompt skepticism rather than duplicating it. The system prompt tells the model to notice unsourced claims; the template tells it where to route them. Separating detection from routing allows independent tuning — if the model detects but misroutes, only the template needs adjustment, and vice versa.

### Regression Safety Net

**Purpose**: Ensure skepticism calibration does not degrade the pipeline's core value — turning legitimate braindumps into useful structured analysis.

The regression suite is not an afterthought bolted on at validation time. It is a first-class design constraint that shapes every prompt change. Each tuning iteration is scored against both the BullshitBench tuning set (does pushback improve?) and the legitimate braindump suite (does helpfulness degrade?). A change that improves BullshitBench score but introduces false-positive skepticism on real inputs is rejected.

The regression suite covers the product's actual input distribution: technical braindumps with real metrics, vague braindumps with no numbers at all, braindumps referencing niche-but-real tools, and braindumps with domain jargon the model might not recognize. The last category is the hardest edge case — the line between "niche real framework" and "fabricated framework" is exactly where false positives would emerge.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| AI adapter | `adapter.rewrite()` with Opus 4.6 | Existing pipeline call; no new adapter methods or providers needed. Changes are in the prompt arguments, not the adapter interface. |
| System prompt | Preamble text modification | The system prompt string passed to `adapter.rewrite()` is the intervention point. No new configuration surface — the prompt text itself is the artifact. |
| Analysis template | Template text modification | The structured template that constrains output format. Section definitions are the channeling mechanism. Same template string, refined section instructions. |
| Evaluation data | Flat files in project directory | BullshitBench split files and regression suite braindumps stored as project data. No database, no new endpoints, no scoring infrastructure. |
| Scoring | Manual rubric (0/1/2 per question) | Automated scoring would require a second LLM call to judge output quality — overhead that exceeds the value for a 100-question benchmark. Manual scoring on 60 tuning questions is ~30 minutes per iteration. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Two-layer intervention (system prompt + template) instead of template-only | The specificity_trap and plausible_nonexistent_framework weaknesses fail at different stages. Specifics bypass detection entirely (the model doesn't notice they're suspicious); frameworks bypass routing (the model notices but still treats them as given). A template-only fix can redirect flagged claims but cannot make the model flag them in the first place. The system prompt preamble is the only lever that affects the model's detection posture before it encounters the template's routing instructions. | Increases the tuning surface area — two independent text changes that could interact in unexpected ways. Mitigated by the holdout split: tune on 60%, validate on 40%, catch interaction effects before shipping. |
| Single generic skepticism posture instead of domain-specific prompts | Finance (1.20 mean) and legal (1.29 mean) are the weakest domains, suggesting domain-specific prompts. But the two weakest techniques (specificity_trap and plausible_nonexistent_framework) span all domains — finance and legal just have more questions using those techniques. Fixing the technique-level weakness should lift domain scores without domain-specific branching. | If domain scores don't improve after technique-level fixes, we've left points on the table. But adding domain routing means the anonymous pipeline needs to classify input domain before analysis — a second LLM call or a fragile heuristic, violating the single-pass constraint. Measure first; add domain branching only if technique-level fixes plateau below 80%. |
| 60/40 tuning/holdout split instead of k-fold cross-validation | Cross-validation is overkill for prompt tuning on 100 questions. Each fold would require a full pipeline run (expensive in tokens and time), and the small sample sizes per technique (specificity_trap has only 8 questions) make fold-level variance meaningless. A single stratified split gives a clean tuning/validation boundary with enough questions in each technique to measure movement. | The holdout set can only be used once for final validation — repeated peeking invalidates it. If the first validation fails and we need another tuning round, we're measuring against a set we've already seen. Acceptable for a 100-question benchmark where the goal is directional improvement, not statistical rigor. |
| Route unverified claims to Open Questions instead of rejecting them outright | The pipeline's job is analysis, not fact-checking. A braindump mentioning "the Henderson-Kraft protocol" might reference something real that the model's training data doesn't cover. Routing it to Open Questions with an "unverified — needs validation" flag preserves the analysis while surfacing the uncertainty. Outright rejection ("this doesn't exist") would be correct for BullshitBench but catastrophic for a user who referenced a real niche framework. | Routing to Open Questions scores lower on BullshitBench than outright rejection (score 1 vs score 2 in many rubric interpretations). This means the theoretical ceiling is lower than raw Opus 4.6's 89.7%. Acceptable — the target is 82–85%, not 90%, and product credibility matters more than benchmark rank. |
| Manual scoring instead of automated LLM-as-judge | An automated scorer would speed up tuning iterations but introduces a second LLM call per question (100 calls per iteration), adds variance from the judge model's own interpretation of the rubric, and creates a meta-optimization problem where prompt changes could game the judge rather than improve actual skepticism. | Manual scoring limits iteration speed to ~30 minutes per tuning cycle. At the expected 3–5 tuning iterations, this is 2.5 hours total — well within the time budget for a 4-day epic. If future benchmarking becomes routine, revisit automated scoring as a separate capability. |
| Conditional skepticism (triggers on universal claims, not user-attributed data) rather than blanket skepticism | Blanket skepticism ("question all specific numbers") would catch fabricated metrics but would also flag legitimate user data ("our p99 went from 120ms to 460ms after the migration"). The distinction between "the user measured X" and "X is an established fact" is the calibration line that preserves helpfulness while catching nonsense. | Harder to phrase precisely in a prompt — the model must infer attribution from context clues, not explicit markers. Braindumps don't label claims as "my data" vs "domain fact." The model will make judgment calls, and some will be wrong. The regression suite catches systematic mis-calibration; individual edge cases are acceptable at the 82–85% target. |

## Risk Considerations

**Overfitting to BullshitBench phrasing**: The 100 questions have specific phrasing patterns. Prompt changes tuned on 60 of them might exploit those patterns rather than building genuine skepticism. The holdout set mitigates this for BullshitBench itself, but the regression suite is the real guard — it tests whether skepticism generalizes to legitimate inputs, which is the actual product requirement.

**Skepticism bleed into legitimate analysis**: The highest-risk failure mode. A braindump about "implementing the CQRS pattern with event sourcing" should be analyzed helpfully, not flagged as an unverifiable framework — even though it pattern-matches "named methodology." The system prompt's conditional trigger (unfamiliar named methodologies, not all named methodologies) is the calibration mechanism, but "unfamiliar" is subjective to the model's training data. The regression suite must include braindumps with niche-but-real concepts to catch this.

**Interaction effects between prompt layers**: The system prompt preamble and the template section instructions could conflict — the preamble might flag a claim that the template then routes to Hard Constraints anyway, or the preamble's skepticism might override the template's channeling and produce output that doesn't fit the structured format. Testing each layer independently before combining them isolates interaction effects.

## Related Documents

- [Analysis](./analysis.md) — Baseline BullshitBench results and failure pattern identification driving this design
- [Epic](./epic.md) — Scope, task breakdown, and success criteria for the intervention
- [Timeline](./timeline.md) — Execution status and delivery tracking