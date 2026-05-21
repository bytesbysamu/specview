# 🎯 Epic: BullshitBench Eval

## Business Value

Specview's anonymous analysis pipeline claims to challenge bad ideas — but that claim has no structured proof. A single manual test (the "Causal Dependency Fingerprinting" question) showed the pipeline catching fabricated methodology and recommending a spreadsheet instead. Anecdote isn't evidence. BullshitBench (petergpt/bullshit-benchmark, 1.6k stars, MIT) provides exactly the structured proof needed: 100 scored questions across 5 domains, 13 documented nonsense techniques, and a public leaderboard where Claude Sonnet 4.6 already leads at 91%. Running Specview's analysis pipeline against this benchmark produces a publishable, reproducible number.

The market opportunity is content-driven. Claude dominates the BullshitBench leaderboard, but no *product built on Claude* has published eval results against it. Specview would be the first tool — not model — to benchmark itself on nonsense detection. The blog post writes itself: "We ran BullshitBench against our spec pipeline. Here's what it caught and what it missed." Tagging Peter Gostev (benchmark creator) creates organic distribution to exactly the audience that cares about AI reliability. Whether the score is high or mediocre, there's a story — either "our analysis layer adds real value" or "here's what we learned about where structured analysis fails."

The eval also creates a repeatable regression artifact. Once the harness exists, re-running after prompt changes or model upgrades takes one command. This is cheap insurance against silent quality degradation — the kind of thing that erodes trust before anyone notices.

## Scope

### What This Epic Covers

- **Eval harness** — CLI script that feeds BullshitBench questions through `adapter.rewrite()` and collects raw responses
- **Automated judging** — Single Sonnet judge scoring each response 0/1/2 against the known nonsensical element
- **Aggregate reporting** — JSON output with scores broken down by domain (software, finance, legal, medical, physics) and nonsense technique (13 categories)
- **Vendored fixtures** — `questions.v2.json` pinned in-repo for reproducibility; no runtime fetching
- **Smoke-test mode** — `--limit N`, `--filter`, `--dry-run`, `--skip-judge` flags for incremental development and cost control

### What This Epic Does NOT Cover

- ❌ **3-judge panel reproduction** — Single judge is sufficient for a blog post; re-scope only if submitting to the official leaderboard
- ❌ **Competitor comparison** — This proves Specview works, not that it beats ChatGPT; re-scope if competitors respond
- ❌ **Pipeline modifications to improve scores** — This is measurement, not optimization; re-scope after results are in
- ❌ **Builder-context variant** — The eval targets the public anonymous path only; a "with principles injected" comparison is a separate eval
- ❌ **CI integration** — One-shot benchmark for content, not a regression gate; re-scope if tracking drift across deploys
- ❌ **Blog post authoring** — The eval produces data; the blog post is a separate deliverable that depends on what the data says

## Tasks

| # | Task | Dependencies | Effort | Parallel | Priority |
|---|------|--------------|--------|----------|----------|
| 1 | **Vendor fixtures & validate model routing** | None | 0.5 days | — | High |
| 2 | **Build eval runner** | 1 | 1.5 days | — | High |
| 3 | **Build judge harness** | 2 | 1 day | — | High |
| 4 | **Aggregate reporting & full run** | 3 | 1 day | — | High |
| 5 | **Document results for blog input** | 4 | 0.5 days | — | Low |

### Task Descriptions

**Task 1 — Vendor fixtures & validate model routing.** Pull `questions.v2.json` from petergpt/bullshit-benchmark, confirm the v2 schema contains question text + known nonsensical element + domain + technique metadata. Critically: confirm which model `CHAIN_PROVIDER=cli` actually invokes via `adapter.rewrite()` — if it's not haiku, the eval isn't measuring what we claim. Resolve the "no principles injection" question by inspecting the anonymous analysis prompt path end-to-end. These are blockers: if the model or prompt isn't what we think, every subsequent task produces invalid data.

**Task 2 — Build eval runner.** CLI script under `specview/api/evals/bullshit_bench/` that iterates questions through `adapter.rewrite()`, captures raw responses, and writes per-question JSON results. Must support `--limit N` (smoke test), `--filter domain` (partial runs), `--dry-run` (prompt construction verification without API calls). Runs via `docker exec` against the existing container — no image rebuild. Sequential execution (CLI provider constraint). Address the runtime estimate: if per-question latency matches the 71.6s manual test, full run is ~120 min, not 30-50 min.

**Task 3 — Build judge harness.** Sonnet-based scoring via the same adapter. Takes question + known nonsensical element + pipeline response, outputs 0/1/2 per the BullshitBench rubric. Must support `--skip-judge` to allow manual review of raw responses before automated scoring. Judge prompt design is the critical dependency — the rubric must be tight enough that scoring is reproducible across runs.

**Task 4 — Aggregate reporting & full run.** Compute aggregate metrics: mean score, percentage scoring ≥1 (any pushback), percentage scoring 2 (clear pushback), broken down by domain and nonsense technique. Decide the headline number before running — mean score / 200 (leaderboard format) vs. percentage with pushback. Execute the full 100-question run, capture results, validate that smoke-test scores are consistent with full-run scores.

**Task 5 — Document results for blog input.** Summarize findings in a structured format the blog post can consume: headline metric, strongest/weakest domains, most/least caught nonsense techniques, notable individual responses (best catches, worst misses). This is raw material, not the blog post itself.

## Success Criteria

- ✅ All 100 BullshitBench v2 questions processed through `adapter.rewrite()` with confirmed model identity
- ✅ Each response scored 0/1/2 by automated Sonnet judge with per-question JSON output
- ✅ Aggregate metrics computed by domain (5) and nonsense technique (13) — no manual calculation
- ✅ `--dry-run` confirms prompt construction without API spend; `--limit 3` completes in under 5 minutes
- ✅ Full run is reproducible — same vendored questions, same pipeline config, same judge prompt yields consistent scores (±2% on re-run)
- ✅ Results structured for direct use in blog post — headline number, domain breakdown, notable examples identified

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) — System design for eval harness, judge, and reporting
- [Timeline](./timeline.md) — Status tracking and milestone dates