# Improve Specview's BullshitBench Score

## Baseline

We ran BullshitBench v2 (100 questions, 5 domains, 13 nonsense techniques) against Specview's anonymous analysis pipeline. The pipeline uses adapter.rewrite() with Opus 4.6, system prompt "You are a markdown spec writer", and a structured analysis template that constrains output to 30-40 lines of markdown.

**Current score: 74.2% (rank ~17 of 158 models)**

- Mean score: 1.485 / 2.0
- Clear pushback (score 2): 69.7%
- Partial pushback (score 1): 9.1%  
- Accepted nonsense (score 0): 21.2%
- 1 question hit a usage policy error

For comparison, raw Opus 4.6 without pipeline constraints scores 89.7% (rank 5). The pipeline costs us ~15 percentage points.

## Where we're strong

Three techniques at perfect 2.0 mean: authoritative_framing (9/9), reified_metaphor (3/3), wrong_unit_of_analysis (5/5). Also near-perfect: misapplied_mechanism (1.85, 13 questions), nested_nonsense (1.71, 7 questions). Physics domain is strongest at 1.73 mean, software at 1.55.

The pipeline naturally catches nonsense that contradicts well-known principles or applies mechanisms from wrong domains. The structured format ("Open Questions", "Hard Constraints") gives the model natural places to express skepticism.

## Where we're weak

**specificity_trap: 0.25 mean (1/8 caught)** — questions with fabricated but hyper-specific numbers, percentages, or thresholds. The pipeline treats these as hard constraints and builds around them. Example: fake benchmark numbers, invented conversion rates, fabricated regulatory thresholds.

**plausible_nonexistent_framework: 1.06 mean (8/16 caught)** — fabricated methodologies with real-sounding names like "differential indemnity decomposition". The pipeline's job is to analyze braindumps, not fact-check them, so it treats named frameworks as given context and builds analysis around them.

**Finance domain: 1.20 mean (40% accepted)** — weakest domain. Financial nonsense with plausible jargon gets through because the analysis template doesn't prompt for source verification.

**Legal domain: 1.29 mean (29% accepted)** — similar pattern to finance. Legal jargon creates a veneer of authority the pipeline doesn't question.

## The core tension

The analysis pipeline is designed to be helpful — take a messy braindump and produce structured analysis. That helpful posture directly conflicts with skepticism. When someone pastes a braindump mentioning "the Henderson-Kraft protocol for distributed cache invalidation", a helpful spec writer analyzes it; a skeptical reviewer flags it as unverifiable.

Raw Opus 4.6 doesn't have this constraint — it can freely say "this doesn't exist." Our pipeline's structured template forces the model into analyst mode, suppressing its natural pushback instincts.

## What the data suggests

The "Open Questions" section is where pushback naturally lands when it happens. Questions the pipeline catches tend to get flagged there as "needs validation" or "no established precedent." Questions it misses get treated as hard constraints or dependencies.

The specificity trap works because specific numbers feel like facts, not claims. When a braindump says "our p99 latency increased 340ms after the migration" the pipeline has no mechanism to question whether 340ms is real. But when someone says "we need to implement the Fibonacci-Lehmer cache eviction strategy" the pipeline sometimes catches it because the concept feels novel enough to flag.

The partial scores (score 1) are interesting — 9 questions got hedged responses where the pipeline showed discomfort but didn't reject. These are the cases where a small prompt nudge might flip them to full pushback.

## Constraints

- The analysis pipeline must remain useful for legitimate braindumps — we can't make it so skeptical that it flags everything
- The system prompt and template are the levers we control; we're not changing the model
- Any changes apply to all braindumps, not just adversarial ones
- The structured output format (The Problem, Hard Constraints, Open Questions, Dependencies, Out of Scope) should stay — it's core to the product
- We use adapter.rewrite() with no context injection — builder context and principles are not available on the anonymous path
- Performance matters — we can't add a second full analysis pass just for skepticism