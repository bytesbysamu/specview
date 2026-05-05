# 🔍 Express Retirement: Full Flask API Migration: A — Analysis

## The Problem
Express hosts 5 remaining AI text endpoints while Flask (port 3101) already owns projects, context files, and `/rewrite`. The proxy routes known Flask endpoints; Express handles the rest. The split means two runtimes, two error shapes, and two codebases to maintain — migration closes this.

## Hard Constraints
- `===FILE: filename===` is a contract with the Angular parser — Flask must pass `generate-spec` output as raw text, no JSON wrapping, no format variation.
- Anthropic SDK (not `spawn`) is the AI transport — no exceptions unless API key is absent.
- One Flask `errorhandler`, consistent error envelopes — no per-route error shapes.
- `openapi.yaml` drives DTO generation; generated artifacts are gitignored and regenerated on build.
- `review` JSON extraction stays inline (`json.loads(re.sub(...))`) — one consumer, no shared utility.

## Open Questions
- Does `generate-spec` stream? Streaming preserves the marker format by default; buffered response requires explicit passthrough logic. Which mode is Express using today?
- "Task 3 already specced in Phase 2" — is `/generate` already implemented in Flask, or only specced? Does this epic cover 4 endpoints or 5?
- Express shutdown: retire immediately after the last endpoint migrates, or leave running as fallback? Determines whether the proxy needs a fallback route or can drop Express entirely.

## Dependencies & Sequencing
- Each migrated endpoint must be added to the Angular proxy before Express can stop serving it — proxy update and Flask route are atomic per endpoint.
- `generate-spec` marker format must be validated against the Angular parser before that endpoint is considered done — the parser is the acceptance test.
- `lint-braindump` and `review` can migrate in parallel; `generate-spec` goes last (highest contract risk).
- Express can only be retired after all 5 endpoints are proxied and smoke-tested.

## Explicitly Out of Scope
- Shared JSON fence-stripping utility — one consumer exists (`review`), no second named; extract only when a second consumer appears.
- Retry/backoff on AI calls — no named failure case in this migration; defer until a route fails in production with a retriable error.
- Any behavior changes to the 5 endpoints — this is parity migration. New behavior belongs in a separate epic.
- Express as a long-term fallback post-migration — no stated benefit, adds maintenance surface.