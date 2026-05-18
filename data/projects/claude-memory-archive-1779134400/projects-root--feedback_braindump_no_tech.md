---
name: Brain dumps stay free of technical decisions
description: Sam strips API shapes, schema choices, module paths, component names from brain dumps — those belong in architecture/spec-doc output, not the input
type: feedback
---

Brain dumps capture **what** the feature is and **why** it matters (scope, UX surface, success criteria, out-of-scope list). They do NOT capture API endpoints, request/response shapes, schema decisions (new table vs overload), module paths, component names, lazy-route structure, or ENABLED_MODULES registration. Those are architecture/spec-doc territory.

**Why:** The spec-doc pipeline reads codebase.md, principles.md, and references.md — it has more context than a human brain dump author. When the brain dump hardcodes a technical decision, the pipeline doesn't get to make it using that context. Over time this produces worse specs than letting the pipeline decide.

**How to apply:** When iterating or writing brain dumps, strip anything of the form: `POST /api/...`, `persist to X table`, `new lazy-loaded route at src/app/pages/...`, `ServiceName`, `ComponentName`, `feature-registry entry: path 'X'`. Rewrite as user outcome: "users can run operations on text through the existing chain primitive" — not "POST /api/text/rewrite goes through chain adapter".

**Edge case — hard constraints:** if the brain dump names a constraint that's ALREADY in principles.md (ORM, OpenAPI-first, feature-registry pattern, rate limiting), it's redundant and still counts as over-specifying. Principles get injected into the prompt anyway.

**Related signal:** the "typist vs designer" quality metric from the 2026-04-16 task-2 retro. Over-specified brain dumps feed over-specified specs that make executors typists — short-term correct, long-term brittle because the spec compresses the design work into a single moment (the brain dump) instead of letting it happen at the right layer (architecture).
