---
sidebar_position: 1
---

# 🔍 Batch Task Generation – Analysis

**Purpose**: Identify problems driving this capability.

**Date**: 2026-04-17

---

## Summary

- **Problem**: Half of the 11 shipped epics lack implementation guides because agents wrote directly to worktrees without going through `regen-task.mjs`
- **Hard Constraints**: Must use existing `regen-task.mjs --all --parallel 2` per-project; no new API endpoints; concurrency capped at 2 (evidence: 2–3 works, 5+ fails)
- **Open Questions**: Whether to introduce a `--retroactive` flag that injects git diffs as generation context (deferred — generate from epic + architecture for now)
- **Dependencies**: Requires the Express API running on port 3100 (`npm run api`) with Claude CLI configured; depends on `--all` and `--parallel` flags already shipped in regen-task.mjs
- **Explicitly Out of Scope**: New AI provider integration, changes to the generation prompt template, quality improvements to individual task specs, git-diff-aware retroactive generation

---

## Issue Breakdown

### Operational Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No cross-project batch execution — operator runs `regen-task.mjs` per-project manually, 10 sequential invocations for 10 projects | HIGH | Task 2 (batch orchestrator) |
| No project discovery — operator must manually identify which projects have epics without task specs | HIGH | Task 1 (inventory scanner) |
| No unified progress visibility — operator monitors 10 separate terminal sessions or scrolls combined stdout to find failures | HIGH | Task 3 (progress reporting) |
| No failure recovery — if task 4 of 8 fails in a project, the operator must manually figure out which tasks succeeded and re-run the rest | HIGH | Task 4 (failure recovery) |
| No batch-level quality signal — deviation counts and review scores exist per-spec but are never aggregated across a batch run | MEDIUM | Task 5 (summary report) |

### Knowledge Gap Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| 4 shipped epics have working code but no implementation guides — next session re-discovers what this session solved | HIGH | Batch run (retroactive category) |
| 2 unimplemented epics (chain-meta-display, parallel-gen) are blocked on missing task specs — agents can't execute without guides | HIGH | Batch run (ready-to-execute category) |
| 4 backlog epics lack specs — when prioritized, they'll need a spec-generation step before execution, adding latency | MEDIUM | Batch run (backlog category) |

### Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Retroactive spec generation method | Epic + architecture only (no git diff) | `regen-task.mjs` doesn't support `--retroactive` flag; adding it is a separate capability. Intent-based specs are close enough for documentation — the code is the source of truth for details |
| Cross-project concurrency model | Sequential projects, parallel tasks within each | Avoids interleaving stdout from multiple projects; reuses existing `--all --parallel 2` per-project machinery without modification |
| Concurrency limit | 2 | Evidence from parallel-gen testing: 2–3 concurrent API calls work reliably, 5+ cause timeouts. Conservative default with `--parallel` override available |
| Manifest format | JSON file | Machine-readable for retry, human-readable for review. No YAML dependency needed |

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

