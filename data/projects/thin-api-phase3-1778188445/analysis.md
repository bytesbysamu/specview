# 🔍 Thin API Phase 3 — Analysis

## The Problem
`ai.service.ts` hardcodes Claude prompt instructions in TypeScript and routes nine distinct actions through one `/api/ai/text/rewrite` endpoint. Phase 3 flattens the API to action-named routes, moves all instruction strings into SKILL.md files, and deletes the now-redundant Python prompt module.

## Hard Constraints
- Frontend ships zero instruction strings, zero system prompts, zero AI behavior knowledge — facade only
- SKILL.md is the single source of truth for prompt logic; Python routes ~10 lines each
- OpenAPI spec defines the contract; Angular client must be generated, not hand-written
- Project CRUD, auth, billing, `quality/` module are untouched
- Response shape locked: `{ text, latencyMs }`

## Open Questions
- **Route prefix** — braindump contradicts itself: header says flat (`/api/brainstorm`), backend section + Angular example say `/api/text/brainstorm`. Pick one: flat verbs, or `/api/text/*` namespace.
- **Angular client** — generated via `ng-openapi-gen` (header claim), or hand-written thin `AiService` (example code shows this). Can't be both — generated client makes the example file obsolete.
- **Followup brainstorm** — separate `/api/text/brainstorm-followup` route, or single `/api/text/brainstorm` with optional `question`/`context`? Skill-side branching is simpler; pick before openapi.yaml is written.
- **Bootstrap + epic-guide migration** — "Spec generation" section migrates them to skills in Phase 3; "What stays" defers them to Phase 4. Decide before sequencing the deletes.
- **Existing skills** — `brainstorm` and `rewrite` skills exist in `plugin/skills/`; confirm SKILL.md format matches before authoring six new ones.

## Dependencies & Sequencing
- SKILL.md files for expand/compress/clarify/simplify/tldr/bullets must exist before the Flask routes can call them
- `openapi.yaml` finalized before Angular client regeneration
- New `/api/text/*` (or `/api/*`) routes live and verified before old `/rewrite` + `/generate` deleted
- Frontend cut over before `ai.service.ts` instruction strings and `text_prompts.py` are removed
- Bootstrap decision (Phase 3 vs 4) gates whether `task_gen.py` and `workflows/spec_gen/` deletes happen now

## Explicitly Out of Scope
- `bootstrap-project` / `generate-epic-guide` skill migration — defer to Phase 4 per "What stays"; trigger to re-scope: route prefix decision lands and skill pipeline proves trivial
- `task_gen.py` and `quality/` deletions — flagged as "audit separately"; not Phase 3 work
- `/iterate`, `/lint-braindump`, `/review` route logic — already unused; just delete, no replacement
- New `/generate` endpoint — explicitly removed, no migration target
- Auth, billing, project CRUD changes — untouched