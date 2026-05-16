# Specview Self-Review & Improvement Plan

## Session review (2026-05-15 to 2026-05-16)

Created ~15 braindumps, generated specs for most, executed 3 impl guides via /exec-guide, shipped 2 PRs, deleted 4,576 lines of dead code, built a live component playground.

### What worked
- Braindump-to-analysis is the killer feature. Caught the CSS token mismatch root cause, surfaced open questions we hadn't considered, correctly excluded scope-creep items.
- Epic scope exclusions saved hours. Every epic correctly pushed out "cool but not now" ideas.
- Implementation guides gave agents executable work orders. The guide IS the prompt.
- The workflow (dump → structure → review → correct → execute) forced thinking before coding.

### What didn't work
- Impl guides get file paths wrong every time. Used subdirectory paths when project uses flat structure. Root cause: codebase.md context file had no Angular file structure detail. FIXED — updated codebase.md with full file layout.
- Effort estimates are inflated 3-5x. Tasks estimated at 1.5-2 days took 30 min to 2 hours. The pipeline doesn't know Claude Code agent speed.
- Architecture docs are verbose (15-20K). Signal-to-noise drops after page 5. Most content restates analysis + epic.
- Every impl guide needed 3-5 correction notes before execution. The value is "faster to correct than to write from scratch," not "correct out of the box."
- exec-guide ceremony overhead caused work loss. Branch auto-merged before summary was written. Full procedure (test, review, fix, commit, PR, CI, merge, summary) is heavy for small tasks.

### Fixes applied
1. Updated codebase.md with full Angular file structure (flat layout, all component names, services/ as only subdirectory, global styles.css tokens)
2. Updated CLAUDE.md with "always execute full skill procedure" rule
3. Saved memory: commit often, create PR immediately, present tense test names

### Fixes still needed

**Effort calibration:** The prompts should say "Effort estimates assume Claude Code agent execution, not manual developer time. 1 day = ~2 hours of agent time."

**Architecture verbosity:** The architecture prompt could include "Keep under 5,000 words. No restating analysis or epic content — reference them by link instead."

**Auto-correction:** Instead of manual correction notes, the exec-guide skill could automatically read CLAUDE.md and override impl guide conventions (flat paths, test naming, etc.) when dispatching agents.

**Codebase context auto-refresh:** Run a script that regenerates codebase.md from the actual file tree on every commit. The context file drifts from reality over time.

### The meta-insight
Specview makes the right process (think before code) low-friction enough that you actually do it. The AI output is a starting point, not a finished product. The review-and-correct step is where the real value happens — but without the AI generating the first draft, you'd skip the process entirely and just start coding.

---

## Deep Analysis (2026-05-16)

### 1. Key Themes

**AI output as scaffold, not product.** The entire workflow's value proposition isn't "AI writes correct specs" — it's "AI writes something faster than you'd write nothing." The correction step isn't a failure mode; it's the design. This reframes quality expectations permanently.

**Process adoption is a UX problem.** "Think before code" has been known-good practice for decades. Specview didn't invent it — it made it cheaper than skipping it. The insight isn't about AI capability; it's about friction economics.

**Context drift is the silent killer.** Every single failure documented (wrong paths, wrong conventions, wrong estimates) traces back to stale or missing context. The AI's reasoning is fine; the inputs are wrong. This is THE problem to solve.

**Ceremony cost has a breakeven point.** Full procedure (test → review → fix → commit → PR → CI → merge → summary) pays off for large changes but actively destroys value for small ones. Need variable-weight process based on change magnitude.

**Effort estimation is miscalibrated by an order of magnitude.** 3-5x inflation isn't a rounding error — it's a fundamental model mismatch. The system thinks in human-developer-days but executes in agent-minutes.

### 2. Hidden Connections

**Context staleness and effort inflation share a root cause:** the system doesn't observe its own execution. If it watched itself complete tasks in 30 minutes, it would both update its effort model AND notice when file paths don't match reality. Self-observation fixes both.

**"Correction notes" and "codebase.md updates" are the same activity** — teaching the system facts it should already know. Every correction note is a failed context injection. If you're writing the same correction twice, you have a context delivery bug, not a generation quality bug.

**Architecture verbosity and process ceremony are both symptoms of "more = safer" bias.** The system generates 15-20K docs and runs full CI pipelines for 30-minute tasks because nothing tells it when to stop. Both need an explicit "proportionality signal."

**High-level reasoning is excellent; low-level factual grounding is terrible.** The braindump catching CSS token mismatch and the impl guide getting file paths wrong are paradoxical. The system is better at thinking than at knowing. Invest in grounding infrastructure, not reasoning improvements.

### 3. Open Questions

**How to auto-detect change magnitude to scale ceremony proportionally?**
- Option A: Lines-changed threshold (< 50 lines = lightweight, > 200 = full procedure)
- Option B: Agent self-assessment before execution
- Option C: Time-boxed — if done in < 30 min, skip full ceremony retroactively
- Recommended: Option A. Objective, no AI judgment needed, implementable as a conditional in exec-guide today.

**Should codebase.md be regenerated on every commit, or only on structural changes?**
- Option A: Git hook on every commit
- Option B: Only trigger when files are added/deleted/moved
- Option C: Diff codebase.md against reality on exec-guide start
- Recommended: Option B. Every-commit is wasteful; start-of-execution is too late if the guide was already generated from stale context.

**Where does effort calibration live?**
- Option A: Static multiplier in the prompt ("divide human estimates by 4")
- Option B: Historical execution log
- Option C: Remove effort estimates entirely
- Recommended: Option C. They're not actionable for agent executors and consistently mislead reviewers. Replace with t-shirt sizing (S/M/L).

**Should correction notes feed back into prompt templates?**
- Option A: Accumulate corrections into prompts quarterly
- Option B: CLAUDE.md acts as live override layer
- Option C: Auto-append to prompt template after 2+ occurrences
- Recommended: Option B. Already working, inspectable, doesn't pollute prompts with project-specific quirks.

**Is 5,000 words the right architecture doc cap?**
- Option A: Hard word cap with prioritize-novel instruction
- Option B: Structured template with per-section max lengths
- Option C: Architecture becomes thin "decisions + rationale" layer; detail lives in impl guide
- Recommended: Option C. Architecture's unique value is recording WHY, not WHAT.

### 4. Ideas to Explore

**Execution telemetry layer.** Every exec-guide run logs: estimated effort, actual duration, corrections applied, files touched. After 20 runs, ground truth for calibration + auto-detect recurring correction patterns.

**Lightweight mode for exec-guide.** If impl guide touches < 3 files and < 100 lines, skip PR creation and CI — just commit to branch. Recoverable via git, not worth full ceremony.

**Context health check before generation.** Before generating an impl guide, diff actual file tree against codebase.md. If drift > threshold, block generation and update context first. Prevention beats correction.

**Replace architecture docs with decision records (ADRs).** Each decision: 200-500 words (context, decision, consequences). No narrative, no restating. Link to analysis for background. Kills verbosity structurally.

**Bidirectional pipeline.** After execution, auto-generate "lessons learned" braindump that feeds back into next cycle's context. System gets smarter per-project, not just per-session.

**Correction budget as quality metric.** Track corrections-per-guide. If consistently 3-5, that's baseline. If a prompt change drops it to 1-2, that's a real improvement.

**Skip analysis→architecture for S-sized tasks.** Under 100 lines, go braindump → impl guide directly. Intermediate artifacts add overhead without proportional value.

**Convention linter for impl guides.** Validate against CLAUDE.md before execution — catch flat-path violations, test naming mismatches, style drift BEFORE the agent starts.
