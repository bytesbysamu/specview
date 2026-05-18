---
name: Braindump style — no explicit tasks
description: Braindumps should be raw context/problems/ideas, NOT structured task lists — specview's spec pipeline generates tasks
type: feedback
---

Braindumps must NOT contain explicit tasks, numbered steps, or implementation checklists. That's the spec pipeline's job (analysis → epic → architecture → impl-guide).

**Why:** The whole point of specview is to transform raw brain dumps into structured specs. Writing tasks in the braindump defeats the purpose and short-circuits the AI chain.

**How to apply:** When writing or refining braindumps, keep them as context-rich problem statements, ideas, references, current state, pain points, and goals. Let `/spec-pipeline` do the structuring.
