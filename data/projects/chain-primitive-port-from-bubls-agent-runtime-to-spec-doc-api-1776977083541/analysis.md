# Chain Primitive Port — Analysis

## The Problem
`/api/ai/text/generate-spec` already runs a four-step pipeline (`analysis → epic → architecture → spec-doc-spec`), encoded as a single Claude call with `===FILE:` string markers. The markers are a fragile implicit contract: no streaming, no per-step testability, no progress visibility for a 30+ second call. The port surfaces the existing structure as executable code and delivers SSE streaming as a direct consequence.

## Hard Constraints
- Flask stays. No framework swap regardless of SSE ergonomics.
- Port bubls's shape with no added abstractions — every deviation from bubls's design requires explicit justification.
- Anthropic SDK only. No `spawn('claude', ...)` path for chain steps.
- Batch `/generate-spec` endpoint survives until streaming has ≥1 week of green dev traffic.
- `openapi.yaml` declares the stream endpoint; generated DTOs are best-effort for the SSE schema (datamodel-codegen limitation acknowledged in brain dump).

## Open Questions
- **`ChainEvent` type**: Brain dump declares it a `dataclass` but the route calls `.model_dump_json()`, which is a Pydantic method. The rest of the codebase uses Pydantic for response shapes — likely should be a Pydantic model, but needs a decision before Task 1.
- **Step failure path**: The `error` ChainEvent type exists but its behavior is unspecified. Does the chain halt-and-emit or propagate the exception? An unhandled exception inside a Flask generator closes the SSE stream silently — this needs a defined answer before Task 4.
- **structlog dependency**: The brain dump says "log via `logger.info()` once Task 4's logger lands" — but Task 4 in *this* epic is the SSE endpoint, not a logger. Is structured logging arriving in a parallel hardening task, or is it assumed already available?
- **context_loader ownership**: The brain dump's route handler calls `read_context()` and passes results into `run_chain()` as inputs. It also implies the runner may call it internally. Which layer owns the context read — route or runner?

## Dependencies & Sequencing
- Tasks 1–3 (runner, prompt split, `SPEC_CHAIN` declaration) are sequential but independently revertible; each can be reviewed and merged alone.
- Task 4 (SSE endpoint) is blocked on Tasks 1–3.
- Task 6 (batch endpoint deletion) is blocked on ≥1 week of Task 4 green traffic — must be a separate PR.
- Angular SSE consumer unblocked after Task 4; tracked in a separate epic.

## Explicitly Out of Scope
- Implementation code blocks in the brain dump — belong in implementation guides, not the epic.
- Signal-capture endpoint — no UX consumer. Trigger: A/B test requirement on prompt variants.
- Retry/backoff per step — no failure data yet. Trigger: first production rate-limit incident.
- Provider routing per step (e.g. Haiku for analysis) — no cost signal. Trigger: cost optimization becomes a named goal.
- Chain composition — trigger: second pipeline shares ≥2 steps with `SPEC_CHAIN`.
- Persistence/resumability — trigger: a chain run exceeds server restart tolerance.
- Chain-call DB table — structlog JSON to stdout is sufficient. Trigger: "sum tokens this week per step" query and log-grep is too slow.