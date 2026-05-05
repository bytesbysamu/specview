# Spec Doc Flask API — Phase 2: AI Text Operations — Analysis

## The Problem

Phase 1 delivered the Flask non-AI surface (projects, context, health) with 67 projects and 94 tests passing. The chain module — adapter, three providers, file_parser, context_loader — is fully ported but unwired. The Angular frontend's AI operations (rewrite, expand, compress, generate-spec, iterate, review, lint-braindump, scan) are hitting dead routes on port 3101.

## Hard Constraints

- Angular frontend must not change: same 7 paths, same request/response shapes, same `{ text, latencyMs }` envelope
- `generate-spec` output must use `===FILE: filename===` markers — Angular parser depends on exact format
- Scan prompt must not ask the model to write files — Claude CLI treats write intent as a tool call and returns a permission stub; the 502 guard from Express (`looksLikeCliRefusal()`) must be replicated
- Provider selected via `AI_PROVIDER` env var (`claude_sdk | cli | mock`) — no new provider mechanism
- Context injection for `generate`, `iterate`, `generate-spec` uses the existing `modules/context/service.py` — no new infrastructure

## Open Questions

- **Module name**: `modules/ai/` or `modules/text/`? Shapes `create_app.py` ENABLED_MODULES and all import paths — needs a decision before any file is created
- **Prompt colocation**: Inline in route handlers (matches Express) vs. extracted to a `prompts/` submodule (pure functions, easier to unit-test without HTTP)? The brain dump signals a preference for testability but doesn't commit
- **`review` fallback contract**: Flask must attempt JSON extraction and fall back to raw string — what does Angular do with a raw string response? If it crashes, the fallback is a lie and the contract needs hardening before shipping

## Dependencies & Sequencing

- Module name must be decided before any files are created — everything imports from it
- Prompt colocation must be decided before routes are written — restructuring after is a refactor, not a wiring task
- Scan CLI-refusal guard must be implemented before scan route is testable — can't validate scan without it
- All 6 `generate`-family routes can be wired in parallel once module name and prompt location are settled; `rewrite` is independent and can go first as a smoke test

## Explicitly Out of Scope

- `POST /api/ai/implement` — SSE streaming + Docker execution; no current non-implementation-runner caller; re-scope when Phase 3 begins
- Streaming on any text endpoint — no `text/event-stream` consumer exists in Angular today; re-scope if a streaming caller is added
- Rate limiting, token counting, retry/backoff — no current consumer; re-scope when usage tracking or a second product sharing this API is added
- New operation types beyond the 7 named — no Angular caller exists; re-scope when a caller is built