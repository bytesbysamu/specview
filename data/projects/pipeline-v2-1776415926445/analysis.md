---
sidebar_position: 1
---

# Pipeline V2 -- Analysis

**Purpose**: Document the five manual interventions that kept deviation counts low during the 21-task session, and why each must be automated.

**Date**: 2026-04-16

---

## Summary

- **Total Issues**: 5
- **Critical**: 2
- **High**: 2
- **Medium**: 1

---

## Core Problem

The spec-doc pipeline produces implementation guides whose quality degrades across tasks because context drifts. Foundation tasks change file paths, introduce new modules, and establish conventions that downstream tasks cannot see unless the operator manually rescans, reviews, injects caveats, and counts deviations. In the 21-task session, manual intervention dropped deviation average from 6.0 to 2.0 -- but that learning lives in the operator's head, not in the pipeline. A second operator (or the same operator next week) starts at 6.0 again.

---

## Issue Breakdown

### Context Freshness Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| `codebase.md` goes stale after foundation tasks ship, causing downstream specs to cite paths that no longer exist or miss new modules entirely | CRITICAL | Task 3: Auto-Rescan |
| Generated specs contain no quality signal before executor launch; deviations discovered only after commit | HIGH | Task 4: Auto-Review |

### Prompt Hygiene Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| LLM sometimes prepends "I now have enough context..." or reasoning preamble; Executor Protocol requires first character to be `#` | HIGH | Task 1: Preamble Strip |
| Environment-specific quirks (Capacitor proxy spying, token file paths, test framework gotchas) rediscovered by each executor run instead of injected once | CRITICAL | Task 2: Caveats Injection |

### Observability Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No automated way to measure spec quality after executor runs; deviation counts done manually by grepping commit bodies | MEDIUM | Task 5: Deviation-Count Parser |

---

## Evidence

| Signal | Data |
|--------|------|
| Session scope | 3 epics, 21 tasks, 90 commits, 8,592 lines, 240 tests, 0 regressions |
| Deviation trend | 6.0 avg (UX Revamp, no interventions) -> 3.0 (Text Chains, advisory review added) -> 2.0 (Trendfy, all manual interventions active) |
| Stale-path deviations killed by manual rescan | 18 (UX Revamp, Task 1 changed token paths that Tasks 2-6 referenced) |
| Advisory review absorption rate | Executors adapted to appended review notes without blocking gate |

---

## Out of Scope

- **Blocking review gate**: Advisory is sufficient. Session evidence (6.0 -> 3.0 with advisory alone) does not justify a blocking gate. If deviation average rises despite advisory, that is the trigger to revisit.
- **Multi-model provider routing**: Pipeline V2 changes the prompt assembly and post-processing stages, not the AI provider layer.
- **Frontend UI for deviation dashboards**: The parser outputs to stdout/file. A UI can wrap it later when there is a second consumer.
- **Cross-project dependency tracking**: Each project's caveats.md is self-contained. Cross-project concerns are out of scope.

---

## Related Documents

- [Epic](./epic.md) -- scope and task breakdown
- [Architecture](./architecture.md) -- technical design for all five changes
