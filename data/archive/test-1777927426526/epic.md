# 🎯 Epic: test

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

No business value can be articulated for this epic because no problem statement was provided. The input "test" does not identify a user-facing need, an internal inefficiency, or a market opportunity. Until a real brain dump is submitted, this section cannot be written without fabricating scope that may contradict the actual intent.

A valid business value section requires: who is experiencing the problem, what they cannot do today, and what becomes possible once the capability ships. None of those elements are present in the current input.

**Value Proposition**: Undefined — resubmit with a real problem statement to unlock this section.

---

## Scope

### What This Epic Covers

- ❓ **Unknown** — no features, workflows, or systems were named in the input.

### What This Epic Does NOT Cover

- ❌ Everything — no scope was defined, so nothing can be bounded. See [Analysis](./analysis.md) for the full list of open questions that must be resolved before scope can be drawn.

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Provide Real Problem Statement** | None | — | 0.5 days | High |
| 2 | **Define Consumer & Success Criteria** | Task 1 | — | 1 day | High |
| 3 | **Scope MVP Feature Set** | Task 2 | — | 1 day | High |
| 4 | **Identify Hard Constraints & Dependencies** | Task 2 | Task 3 | 0.5 days | High |

### Task 1: Provide Real Problem Statement

Replace the "test" input with a brain dump that describes the current broken or missing behavior, who is affected, and at least one decision already made. Without this, every downstream task — architecture, timeline, implementation — is blocked. This is the single highest-leverage action available.

**Port budget**: Minimal (0.5 days) — this is a discovery and writing task, not a build task. No deferrals.

---

### Task 2: Define Consumer & Success Criteria

Identify who uses the capability (internal team, external users, or automated system) and write at least three measurable success criteria in the form "given X, when Y, then Z." These criteria become the acceptance gate for every subsequent task.

**Port budget**: 1 day of stakeholder interviews and criterion drafting. Defer edge-case acceptance scenarios to post-MVP.

---

### Task 3: Scope MVP Feature Set

With a real problem and success criteria in hand, enumerate the 3–5 features that constitute the smallest shippable version. Explicitly list what is deferred and why. This task produces the replacement for the placeholder scope table above.

**Port budget**: 1 day of scoping workshop. Defer all features that do not directly satisfy a stated success criterion.

---

### Task 4: Identify Hard Constraints & Dependencies

Document any external forcing functions (deadlines, partner dependencies, compliance requirements) and internal sequencing constraints. Feed results into [Solution Architecture](./architecture.md) and [Timeline](./timeline.md).

**Port budget**: 0.5 days of dependency mapping. Defer mitigation plans to architecture work.

---

## Success Criteria

- ✅ A real problem statement exists and has been reviewed by at least one stakeholder.
- ✅ Consumer of the capability is named and confirmed.
- ✅ At least three measurable acceptance criteria are written and agreed upon.
- ✅ MVP feature set is bounded: no more than 5 items in scope, all others explicitly deferred.
- ✅ This epic can be handed to an engineer with no follow-up questions about what to build.

---

## Non-Goals

- ❌ **Implementation of any feature** — no feature has been defined yet; building before scoping wastes effort.
- ❌ **Architecture decisions** — see [Solution Architecture](./architecture.md); design work is blocked until scope is confirmed.
- ❌ **Timeline commitments** — see [Timeline](./timeline.md); dates cannot be set against an undefined scope.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview