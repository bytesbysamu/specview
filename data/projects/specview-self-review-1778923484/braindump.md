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
