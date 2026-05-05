# 🔍 Pipeline Self-Improvement — Analysis

## The Problem
The pipeline catches spec bugs (leaked thinking, stale attribution, path drift, test-count mismatches) via human review and hand-fix commits, but never writes those bug classes back into the prompt. A pre-emit linter and coherence pass encode them as machine-checkable rules. A single-line 60-line truncation in `task_gen/service.py:163` is the structural root cause of cross-task contract drift and should be treated as a distinct fix, not bundled with the linter.

## Hard Constraints
- Module surface is `api/modules/quality/` — already decided.
- Error severity blocks generation (502); warning severity writes with `warnings` field — not configurable until a confirmed exception case appears.
- No self-healing retry loop in this epic.
- Lint rule #8 hardcodes 10 numbered sections — must match the current impl-guide template exactly; any template section-count change silently invalidates it.

## Open Questions
- **`versions.md` — file or env-var dict?** The section title implies a new file on disk; the proposed code shows a Python dict populated from `os.environ`. Which is authoritative, and does `bootstrap_project` need to write anything to disk?
- **Coherence badge scope** — the brain dump says Angular surfaces a project-card badge for unresolved coherence flags. Is that Angular change in this epic, or does `POST /coherence` ship headless and the badge is deferred?
- **Lint rule #8 hardcode** — should the expected section count be read from the impl-guide prompt template rather than hardcoded as `10`? Hardcoding creates a silent false-alarm source on template edits.
- **Repair endpoint auth** — does `POST /repair` require the same auth middleware as other project endpoints, and is it safe to call twice (idempotent)?

## Dependencies & Sequencing
- Versions injection (§4) must land before lint rule #3 ships — otherwise valid docs fail the attribution check.
- Structured prior contracts (§3) should precede the coherence pass (§2) — invariants #1 and #7 will flag drift the generator is still producing until §3 lands.
- Repair endpoint (§5) is fully independent — no ordering constraint.

## Explicitly Out of Scope
- Auto-retry / self-healing loop — deferred until linter error rate stabilizes; re-scope when false-positive rate is measured in production.
- Persistent flag history and analytics — deferred until a second consumer of flag data exists.
- Warning-severity auto-fixers — deferred until failure-rate distribution is known.
- Wholesale impl-guide prompt template rewrite — only the prior-contracts context block changes; any broader rewrite requires a separate brain dump.