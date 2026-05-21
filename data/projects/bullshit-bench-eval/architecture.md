# 🏗️ Solution Architecture: BullshitBench Eval

## Architecture Overview

The eval harness is a read-only measurement layer that sits alongside the existing specview pipeline without modifying it. The core insight is that we are not building a testing framework — we are building a probe that feeds structured input into the same `adapter.rewrite()` path that production users hit on specview.dev, then independently scores what comes back. The eval measures the real pipeline, not a simulation of it.

Three components form a sequential chain: a **runner** that iterates vendored questions through the anonymous analysis pipeline, a **judge** that scores each response against BullshitBench's known-nonsensical-element rubric, and a **reporter** that aggregates scores into publishable metrics. All three share the existing adapter boundary — the runner calls through it to invoke the analysis prompt via CLI provider, and the judge calls through it to invoke Sonnet for scoring. No new AI integration points, no new providers, no new prompt paths.

The harness runs entirely inside the existing Docker container via `docker exec`, reading vendored fixtures from the mounted project directory. This eliminates build-deploy friction and guarantees environment parity with production. Sequential execution is a constraint of the CLI provider, but it also means results are deterministic and reproducible — the same vendored input, same pipeline config, and same judge prompt will produce consistent scores across runs.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | Both the eval subject (analysis via haiku) and the judge (scoring via Sonnet) route through `adapter.py`. No direct provider imports anywhere in eval code. The adapter is the only module that knows which model is active. |
| P2 — Thin Layer | The CLI entry point handles argument parsing and orchestration only — no prompt construction, no scoring logic, no aggregation math. Each concern lives in its own module. |
| P4 — No Speculative Abstractions | Single judge, not a configurable panel. One benchmark, not a generic eval framework. No base class for "future benchmarks." Three similar score-aggregation lines are better than a premature `EvalMetrics` abstraction. |
| P5 — OpenAPI-First | Does not apply. This is CLI tooling with no HTTP surface. No new endpoints are introduced. |
| P7 — File Size & Structure | Each component (runner, judge, reporter) is a separate module under 200 lines. Vendored fixtures are data, not code. Named exports only. |

## Component Design

### Fixture Store

**Purpose**: Provide reproducible, version-pinned input that never changes between runs.

The 100-question BullshitBench v2 dataset is vendored as a JSON file at `api/evals/bullshit_bench/fixtures/questions.v2.json`. Vendoring rather than fetching at runtime eliminates network dependencies during two-hour runs, pins the exact question set for reproducibility, and makes the eval entirely self-contained. The file includes every field both the runner and judge need: question text, known nonsensical element, domain classification (software, finance, legal, medical, physics), and nonsense technique metadata (13 categories).

Version pinning is deliberate. BullshitBench could release a v3 that changes questions, adds domains, or revises scoring criteria. A vendored snapshot means our published numbers always correspond to a known, immutable input set. Updating to v3 would be a conscious decision requiring a new eval run, not something that silently changes under us.

### Eval Runner

**Purpose**: Feed each BullshitBench question through the production anonymous analysis pipeline and capture raw responses.

The runner iterates the vendored question set, wrapping each question's text into the same input format a user would paste into specview.dev's anonymous analysis box. It calls `adapter.rewrite()` — the identical function the production pipeline uses — with no builder context and no principles injection. The response is the full analysis markdown that a real user would receive. This is the critical design constraint: the runner must not alter the pipeline in any way, or the eval measures something other than what it claims.

Each question produces a per-question result record containing the original question metadata, the raw pipeline response, wall-clock latency, and any error state. Results are written incrementally after each question — if the process crashes at question 47, questions 1–46 are fully preserved. This is not optional; it is a structural requirement given the run duration.

The runner supports four composable CLI flags. `--limit N` caps question count for smoke testing — three questions should complete in under five minutes, providing fast feedback during development. `--filter domain` restricts to a single domain for targeted investigation. `--dry-run` constructs the full prompt and writes it to the result record without making any adapter call, enabling prompt verification at zero API cost. `--skip-judge` runs the pipeline but leaves score fields empty for manual review. These flags compose freely: `--limit 3 --filter software --dry-run` verifies prompt construction for three software-domain questions with no spend.

**Runtime estimate**: The single manual test clocked 71.6 seconds. At that rate, a full 100-question run takes approximately 120 minutes — significantly longer than the 30–50 minute braindump estimate. The shorter estimate may hold if haiku generates briefer analyses for obviously-nonsensical questions (less to structure, fewer recommendations to make), but the architecture assumes worst-case duration. The runner logs per-question latency so the true distribution becomes visible after the first full run, informing future planning.

### Judge Harness

**Purpose**: Score each pipeline response against BullshitBench's 0/1/2 rubric using an independent model call.

The judge takes three inputs per question: the original question text, the known nonsensical element (from the vendored fixture), and the pipeline's raw analysis response. It produces a score following BullshitBench's rubric — 0 means the pipeline accepted the nonsense without challenge, 1 means partial pushback (noticed something was off but still engaged substantively), 2 means clear identification and rejection of the nonsensical premise.

The judge uses Claude Sonnet routed through the same adapter boundary, creating a two-model architecture within a single eval run. The runner invokes the analysis path (haiku via CLI provider), and the judge invokes Sonnet for scoring. This is the key adapter routing decision: rather than introducing a second adapter instance or swapping environment variables mid-run, the judge passes a model parameter on its adapter call. The adapter already supports model selection at the call site — the judge simply requests Sonnet explicitly while the runner uses the default anonymous-analysis routing. This preserves P1 (single adapter boundary) while supporting two distinct model needs.

The judge operates as a decoupled second pass. The `--skip-judge` flag on the runner produces result files with populated response fields but empty score fields. The judge can then backfill scores against these existing results without re-running the expensive pipeline. This decoupling is essential during development: the judge prompt itself requires calibration, and iterating on prompt wording should not cost another two-hour pipeline run each time.

**Judge prompt design** is the single most important quality lever in this architecture. A spec-analysis pipeline does not push back the way a chat model does — it will never say "this concept is fabricated." Instead, it surfaces concerns indirectly: "this approach lacks supporting evidence," "consider whether a simpler solution exists," "the described methodology has no established precedent." The judge prompt must be anchored on the known nonsensical element specifically, not on general response quality. It must recognize that structural skepticism expressed through spec-analysis language counts as pushback, even when it does not explicitly name the nonsense. Scoring consistency across runs (target: ±2%) depends entirely on how well this prompt is calibrated.

### Reporter

**Purpose**: Transform per-question scores into publishable aggregate metrics along two dimensions.

The reporter reads completed result files and computes breakdowns along **domain** (5 categories) and **nonsense technique** (13 categories from the BullshitBench taxonomy). For each dimension, it produces three metrics: mean score (0.0–2.0 scale), percentage scoring ≥1 (any pushback detected), and percentage scoring 2 (clear, unambiguous pushback).

The headline metric decision is architecturally significant because it determines what the blog post claims. BullshitBench's leaderboard uses mean score divided by total possible (200 points), yielding a percentage like "91%." For a blog post about a product rather than a model, "percentage of questions where Specview pushed back" is more immediately meaningful — it maps to a user-legible value proposition. The reporter computes both formats. The architecture recommends the percentage-with-pushback framing as the primary headline, with the leaderboard-format score included for readers who want to compare against the published model rankings.

The reporter also identifies notable outliers: highest-scoring responses (best catches) and lowest-scoring responses (worst misses), both by absolute score and by deviation from domain average. A question that scored 0 in a domain where the pipeline otherwise scored 1.8 is more interesting than a question that scored 0 in a domain where everything scored low. These outliers become the narrative anchors for the blog post — the specific stories that make aggregate numbers tangible.

### Results Store

**Purpose**: Persist run data in a self-describing format that supports incremental writes, re-judging, and aggregation.

Results live under `api/evals/bullshit_bench/results/` as one JSON file per run, timestamped. Each run file contains a header with run configuration — model identity, provider, CLI flags used, timestamp, and git commit hash — followed by the full array of per-question records. The git commit hash ties results to an exact code state, so if prompt changes or model upgrades shift scores, the provenance is unambiguous.

The per-question record structure serves three distinct consumers without data duplication. The judge reads question text, known element, and response to produce scores. The reporter reads scores, domain, and technique to compute aggregates. The blog post preparation reads notable responses as human-readable analysis text. One record format, three readers — no transformation layer needed between stages.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | None | CLI-only tooling for a solo developer. No web UI, no new endpoints, no frontend work. |
| Runtime | Python 3.11 (existing container) | No new dependencies. Runs via `docker exec` against the live specview container with read-only mount. |
| AI — eval subject | `adapter.rewrite()` via CLI provider | Measures the exact production anonymous-analysis path. Any other invocation would invalidate results. |
| AI — judge | `adapter` via CLI provider, Sonnet model | Same adapter boundary, different model. Sonnet chosen because it leads BullshitBench at 91% — the strongest available nonsense detector for scoring responses. |
| Fixtures | Vendored JSON | Reproducibility. No network dependency. Version-pinned to BullshitBench v2 schema. |
| Output | Timestamped JSON files | Flat files are sufficient for a one-shot benchmark with no query patterns requiring a database. Matches the existing specview convention of file-based project data. |
| Execution environment | In-container via `docker exec` | Environment parity with production. No image rebuild. No new container. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Vendor fixtures rather than fetch at runtime | Pins exact input set. Eliminates network failures during 120-minute runs. Makes the eval self-contained and reproducible across months. | Must manually update if BullshitBench releases v3. Acceptable — we want explicit control over when our input set changes. |
| Single Sonnet judge, not 3-judge panel | BullshitBench's official methodology uses 3 judges for leaderboard submission. We need publishable results for a blog post, not leaderboard placement. Single judge cuts cost and runtime by 3×. | Scores may differ from official leaderboard methodology by a few percentage points. If leaderboard submission becomes a goal, re-scope as a new task — do not pre-build the panel now (P4). |
| Run inside existing container via `docker exec` | Zero build friction. Environment identical to production. Mounted volume at `/home/appuser/projects` provides fixture access without modifying the container image. | Cannot add Python dependencies not already in the container. Not a constraint — the eval uses only stdlib plus the existing adapter and its dependencies. |
| Sequential execution, not parallel | CLI provider spawns `claude -p` subprocesses. Concurrent calls would compete for the same CLI binary, producing unpredictable interleaving and unreliable latency measurements. Sequential is the only safe mode. | Full run takes ~120 minutes. Acceptable for a one-shot benchmark. If future evals need speed, switch to the Anthropic SDK provider which has no subprocess bottleneck. |
| Incremental per-question writes | A two-hour sequential run must survive crashes, container restarts, and network interruptions. Writing a complete result record after each question means partial runs retain full value. | Marginally more file I/O than a single batch write at the end. The reliability gain is worth orders of magnitude more than the nanosecond I/O cost. |
| Runner and judge decoupled via `--skip-judge` | Judge prompt calibration requires inspecting raw responses first to understand how the pipeline expresses skepticism. Decoupling allows iterating on the judge prompt without re-running the two-hour pipeline. | Final end-to-end run requires two passes (or a combined mode). The judge backfill capability — scoring existing result files without re-invoking the pipeline — eliminates the cost of the two-pass workflow. |
| Percentage-with-pushback as headline metric | "X% of nonsensical questions got challenged" is immediately legible to a blog audience. Mean-score-over-200 requires explaining the rubric before the number means anything. | Not directly comparable to BullshitBench leaderboard numbers without conversion. Mitigated by reporting both formats — the leaderboard-compatible number sits alongside the human-readable one. |
| Sonnet as judge model | Sonnet 4.6 leads BullshitBench at 91%, making it the most capable available nonsense detector. A weaker judge might fail to recognize valid pushback expressed through spec-analysis language. | Judging with the same model family that dominates the benchmark creates potential bias toward recognizing Claude-style reasoning patterns. Acceptable because we are scoring Specview's structured analysis output, not raw Claude completions — the pipeline transforms the response significantly through its spec-analysis prompt. |
| No new HTTP endpoints | The eval is a CLI tool for one developer running a one-shot benchmark. Adding REST endpoints would require auth handling, polling infrastructure (P3), and frontend work — none of which serves the use case or produces user value. | Cannot trigger evals from the specview web UI. Not needed. If evals become a recurring feature (CI regression gate), re-scope with proper HTTP surface then. |
| Git commit hash in result metadata | Ties every result file to an exact code state. When prompt tuning or model upgrades shift scores, the commit hash makes provenance unambiguous. Essential for the "reproducible regression artifact" value proposition. | Requires git access inside the container. Already available — the codebase is mounted into the container at runtime. |

## Open Questions Resolved by This Architecture

**Which model does the anonymous analysis path actually invoke?** The architecture assumes haiku via `adapter.rewrite()` with `CHAIN_PROVIDER=cli`, but this must be verified in Task 1 before any results are generated. If the CLI provider routes to a different model, every score is attributed to the wrong model. Verification is a hard prerequisite — the runner should log confirmed model identity in the result header.

**Does the anonymous path inject builder context or principles?** The architecture requires confirmation that the anonymous analysis path sends only the braindump text with no builder profile or engineering principles attached. If principles like "no speculative abstractions" are injected, the eval measures "analysis + Sam's engineering heuristics" rather than "analysis alone" — a meaningfully different and less generalizable claim. The manual test result (which caught a principles violation) suggests context may already be leaking into anonymous analysis. Task 1 must trace the prompt construction end-to-end.

**Is the 30–50 minute full-run estimate realistic?** No. The architecture designs for ~120 minutes based on the 71.6-second manual observation. The actual distribution will only be known after the first full run, which is why per-question latency logging and incremental writes are structural requirements, not optimizations. If the true median latency is significantly lower than 71.6 seconds, future runs benefit — but the architecture never assumes the optimistic case.

**What does "pushback" look like in spec-analysis language?** The manual test showed the pipeline expressing skepticism through spec-native framing: "solution looking for a problem," "consider a spreadsheet instead." The judge prompt must be designed to recognize this indirect challenge style as valid pushback, not just explicit statements like "this concept is fabricated." This understanding informs the judge prompt design in Task 3 and is why `--skip-judge` exists — raw response inspection must precede judge calibration.

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this architecture
- [Epic](./epic.md) — Scope, tasks, and success criteria for BullshitBench eval
- [Timeline](./timeline.md) — Status tracking and milestone dates