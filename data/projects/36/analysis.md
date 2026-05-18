# 🔍 Specview — Analysis

## The Problem
Two coupled pains in one repo: braindump → structured spec set is manual and context-heavy, and dev sessions on Specview itself drift from Flask/Angular/chain conventions every time. Specview automates the pipeline via `bootstrap-project` and ships a Claude Code plugin that encodes conventions in `references/*.md` so skills and agents route work without re-establishing context.

## Hard Constraints
- `CHAIN_PROVIDER=cli` always in Docker — container cannot reach Anthropic directly; SDK path is forbidden.
- Angular signals-only — no `BehaviorSubject`, no `Observable` for local state, no `*ngIf`/`*ngFor`.
- Feature modules import only from `chain/adapter.py`, never `providers/*` — enforced by `test_structural.py`.
- `session.commit()` lives in service functions, never routes; Blueprints prefixed `/api/{name}`.
- All AI routes gated by `@require_auth` + `@check_usage_limit` — no exceptions.
- Convention rules live once in `plugin/references/*.md`; agents/skills cite, never duplicate.
- No direct push to master — PR + green pytest required.
- Spec storage is markdown on disk at `data/spec-doc/projects/{slug}/` — no DB.
- Stack pinned: Flask (Python 3.11) + Angular 19 + static nginx landing, Docker Compose on Coolify.

## Open Questions
- Modularize `api/modules/ai/` now or wait? — (a) split per workflow type now, (b) wait until N>5 workflows, (c) leave as-is indefinitely.
- Deployment automation — (a) keep manual `git pull + compose build`, (b) GitHub Actions → SSH deploy, (c) Coolify webhook on master.
- Does `dev-review` parallel fan-out merge results, or are three reports returned verbatim?
- Auth on `bootstrap-project` itself — same `@require_auth` + usage limit, or unauth'd internal call?

## Dependencies & Sequencing
- Plugin references must exist before any skill/agent can cite them — references are upstream of all routing.
- `spec-pipeline` (bootstrap API) blocks `impl-guide`, which blocks `exec-guide` — pipeline is strictly ordered.
- `chain-agent` provider config blocks every AI workflow — no AI feature ships before CLI provider is healthy in container.
- Structural test (`test_structural.py`) blocks any refactor that touches adapter boundaries.

## Explicitly Out of Scope
- SDK provider path in Docker — locked to CLI; trigger to revisit only if container gains outbound Anthropic access.
- Database-backed spec storage — markdown-on-disk is the contract; revisit only if multi-user concurrent edits land.
- CI-triggered auto-deploy — explicitly deferred to open question; do not bake into epic.
- NgRx or any external Angular state lib — signals-only is non-negotiable.
- Inline convention docs in skills/agents — must reference `plugin/references/*.md`; trigger to revisit is never.
- New skills/agents beyond the existing 9 + 4 — out of scope for this epic unless braindump explicitly adds one.