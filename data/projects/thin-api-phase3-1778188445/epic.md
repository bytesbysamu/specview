# 🎯 Epic: Thin API Phase 3

## Business Value

Phase 3 closes the architectural loop opened by Phase 2: prompt logic stops leaking into the frontend. Today, `ai.service.ts` ships hardcoded Claude instruction strings to every browser, which means improving a brainstorm prompt requires an Angular rebuild and deploy. Nine distinct user actions all funnel through `/api/ai/text/rewrite` with caller-supplied instructions — the API is a passthrough, not a contract. Flattening the surface to action-named routes (`/api/brainstorm`, `/api/expand`, etc.) and moving every instruction into SKILL.md gives the backend sole ownership of AI behavior.

The payoff is iteration speed. Prompt tuning becomes a SKILL.md edit + skill reload — no frontend deploy, no TypeScript review cycle, no client cache invalidation. New text actions become a three-file change (openapi.yaml + SKILL.md + 10-line Flask route), and the Angular client regenerates from the spec. For a solo founder shipping across five projects, collapsing "tweak the brainstorm prompt" from a deploy to a file save is the entire point.

This is internal infrastructure for spec-doc — Sam pays for it in time saved on every prompt iteration across humanize-me, Bubls, and Trendfy specs generated through this tool.

## Scope

### What This Epic Covers
- **Flat action-named routes** — eight `/api/<action>` endpoints replacing the single `/rewrite` passthrough (brainstorm, expand, compress, clarify, simplify, tldr, bullets, rewrite)
- **SKILL.md authoring** — six new skill files for expand/compress/clarify/simplify/tldr/bullets; brainstorm and rewrite skills already exist
- **OpenAPI-first contract** — `openapi.yaml` defines the eight routes; Angular client is regenerated, not hand-written
- **Frontend facade cutover** — `ai.service.ts` becomes a thin wrapper around the generated client; zero instruction strings remain
- **Followup brainstorm consolidation** — `{ text, question?, context? }` on the single brainstorm route; skill branches on payload shape
- **Dead code deletion** — old `/api/ai/text/rewrite`, `/generate`, `/iterate`, `/lint-braindump`, `/review` routes plus `text_prompts.py` and its tests

### What This Epic Does NOT Cover
- ❌ **Bootstrap-project skill migration** — deferred to Phase 4; analysis flagged the braindump contradiction and "What stays" wins
- ❌ **Generate-epic-guide skill migration** — same deferral; route stays Python-backed for Phase 3
- ❌ **`task_gen.py` deletion** — still used by active routes; audit separately per "What stays"
- ❌ **`quality/` module changes** — out of scope, in use by active routes
- ❌ **`/generate` replacement** — removed with no equivalent; not a clear business action
- ❌ **Auth, billing, project CRUD** — untouched; this is an AI-routes-only refactor
- ❌ **Response shape changes** — locked to `{ text, latencyMs }`; breaking the contract is out of scope

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Author six new SKILL.md files** (expand, compress, clarify, simplify, tldr, bullets) matching existing brainstorm/rewrite format | None | Yes (with #2) | 1 day | High |
| 2 | **Define OpenAPI contract** for eight `/api/<action>` routes with locked `{ text, latencyMs }` response shape | None | Yes (with #1) | 0.5 day | High |
| 3 | **Implement Flask `/api/text` blueprint** — eight thin route handlers (~10 LOC each) calling skills; brainstorm route accepts optional `question`/`context` | 1, 2 | — | 1 day | High |
| 4 | **Regenerate Angular client + cut over `ai.service.ts`** to facade-only methods; remove all instruction strings and `followupBrainstorm` prompt assembly | 2, 3 | — | 1 day | High |
| 5 | **Delete dead Python and TypeScript** — old `/rewrite`, `/generate`, `/iterate`, `/lint-braindump`, `/review` routes; `text_prompts.py` + tests; legacy instruction constants | 4 | — | 0.5 day | Low |

## Success Criteria

- ✅ Eight `/api/<action>` routes return `{ text, latencyMs }` and route through SKILL.md (no inline prompt strings in Python route handlers)
- ✅ `ai.service.ts` contains zero instruction strings, zero system prompts, zero `join('\n')` prompt assembly
- ✅ Angular client is regenerated from `openapi.yaml`; `ng-openapi-gen` is part of the build pipeline
- ✅ Each new Flask route handler is under 15 lines (validate input → call skill → return response)
- ✅ Followup brainstorm works through `/api/brainstorm` with `question`/`context` payload — no separate route needed
- ✅ `text_prompts.py` is deleted; no remaining import references in the codebase
- ✅ Old `/api/ai/text/rewrite` and `/generate` return 404; humanize-me + spec-doc UIs still function end-to-end
- ✅ Adding a hypothetical ninth text action requires only: openapi.yaml entry + SKILL.md + 10-line route (verified by walkthrough)

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking