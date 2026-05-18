---
name: Deviation count is the spec-quality verdict on every executor run
description: After any executor run (single or parallel), count Deviations: lines per task — 0–4 normal, 10+ means the spec was underspecified and the pipeline needs correction
type: feedback
originSessionId: ddd9becd-d854-4163-892e-00f6ecd0b63d
---
Sam's rule, applied per executor run: **count deviations per task body**. The "judgment-calls-per-commit is the spec-quality metric" principle in `principles.md` extends to a per-task threshold during review.

- **0–4 deviations across a task's commits**: spec is calibrated; ship it
- **5–9**: borderline; note the categories of drift (path errors, missing context, scope ambiguity) for future spec-prompt work
- **10+**: spec was underspecified; the spec-generation prompt needs correction before the next batch

**IMPORTANT: not all deviations are equal.** Before flagging a 10+ count as a prompt defect, categorize:

| Category | Fix | Treat as defect? |
|---|---|---|
| **Path/token references to things that don't exist yet** (downstream task depends on upstream Task N's output, but spec was generated before N landed) | Re-scan codebase.md between dependent tasks; regenerate downstream specs against fresh context | Sequencing issue, not prompt issue |
| **Spec silent on UX micro-decision** (pill position, icon choice, full-bleed content) | UX-heavy tasks need a visual-design spec in addition to the executor brief | Scope-shape issue — the generator produces executor briefs, not design briefs |
| **Commit-plan drift** (tests bundled, file moves) | Acceptable executor judgment | Minor |
| **Spec-logic mismatch with library reality** (e.g. `@capacitor/status-bar` is a Proxy, can't spy directly) | Feed the generator a "known caveats" reference | Prompt fix |

Only the last category is a true prompt defect. A task hitting 11 deviations split as 5 UX-silent + 5 stale-context + 1 minor is **not** a spec-prompt failure — it's a scope-shape issue for UX tasks and a sequencing issue for chained tasks.

**The stronger retrospective signal:** did §10 Out of Scope hold firm? Zero absorbed scope across N parallel agents is the real test of the executor contract — worth more attention than the deviation count alone.

**Why:** parallel executor runs are also a parallel quality test of N specs at once. Calling out the underspecified one is more valuable than celebrating the others. Skipping the count means the pipeline drifts unmonitored — exactly the failure mode the metric exists to catch.

**How to apply:**
- After every batch of executor runs, surface a deviation table: one row per task, total deviation count, brief categorization.
- If any task crosses the 10+ threshold, flag it to Sam as a spec-prompt issue, not an executor issue. Propose what to add to the prompt template before the next batch.
- The count includes both `Deviations Allowed` clauses the executor invoked AND any `Deviation:` lines in commit bodies.
