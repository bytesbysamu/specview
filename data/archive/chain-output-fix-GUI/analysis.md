---
sidebar_position: 1
---

# Analysis -- Chain Output Fix

**Purpose**: Surface root causes for the three interacting bugs in the braindump-to-docs chain, identify constraints, and resolve open questions before scoping the fix.

**Date**: 2026-04-17

---

## Problem

Three bugs interact in the Bubls braindump-to-docs chain to produce broken output for the Brain Dump GUI button:

1. **Generate step produces conversational text** -- Step 2 (generate) sometimes returns prose like "Alright, here's what I'm seeing..." instead of structured output with `===FILE: spec-index.md===` markers. The context prompt at `server/context/prompts/braindump-to-docs.md` has the file-marker template but lacks the explicit instructions, section-level detail, and "300+ words per file" enforcement that makes spec-doc's `server.js` generate-spec prompt reliable. The LLM treats the lightweight template as a suggestion rather than a format constraint.

2. **Review step scores empty/malformed input** -- When Step 2 fails to produce file markers, the `parse_multi_file_output()` call in the runner returns an empty list or the raw conversational text. Step 3 (review, `outputKey: "score"`) then scores this garbage input against the quality rubric and produces an all-zeros JSON blob. The review step has no way to know its input is invalid -- it faithfully scores whatever it receives.

3. **User sees quality JSON instead of specs** -- With the outputKey sidecar fix shipped (Chain Runner Fix epic), the review score correctly goes to `meta` and `current_text` retains Step 2's output. But when Step 2's output is conversational text without file markers, the user sees that conversational junk as the final output. The sidecar fix is necessary but not sufficient -- the generate step itself must produce valid output.

## Hard Constraints

- **Chain adapter is the only Claude boundary** -- prompt changes live in `server/context/prompts/braindump-to-docs.md`; runner changes live in `server/modules/chain/definition_runner.py`. No changes to `adapter.py` or provider code.
- **Existing chains must not regress** -- `deep-humanize` and `rewrite-review` chains use neither file markers nor `outputKey`. Their behavior must be identical after the fix.
- **The outputKey sidecar fix is already shipped** -- the runner correctly sidecars `outputKey` step results to `meta`. This epic does not re-fix that behavior; it addresses the upstream generate step failure.
- **The prompt fix is the companion epic** -- the detailed template content (what sections, what headings, what format) is scoped in the Port Spec-Doc Template epic. This epic adds the runner guard and ensures the chain fails gracefully when the generate step produces invalid output.

## Open Questions (resolved)

| Question | Resolution | Rationale |
|---|---|---|
| Is the conversational tone a system-prompt issue? | Likely yes -- investigate whether CLI provider passes context blocks as system messages or user messages. | A context block treated as a user message would explain the LLM responding conversationally ("Alright, here's what I'm seeing...") instead of following the format. The CLI provider should pass context as system prompt. |
| Should the runner guard fail the entire chain or just skip review? | Fail the chain with a clear error. | Forwarding invalid output to review produces misleading zero scores. A clear error ("Generate step produced no file markers -- check the braindump-to-docs prompt") is more useful than silent garbage. |
| Should the guard check for `===FILE:` markers or delegate to `parse_multi_file_output()`? | Check for at least one `===FILE:` marker string before calling the parser. | The parser returns an empty list for no markers but does not raise an error. A pre-parse guard with a clear error message is more debuggable than an empty-list check after parsing. |
| Should the guard apply to all chains or only multi-file chains? | Only multi-file chains (`output_mode == "multi-file"`). | Single-output chains (deep-humanize, rewrite-review) have no file-marker expectation. The guard only applies when the chain definition declares multi-file output and a step is expected to produce markers. |

## Dependencies

| Dependency | Status | Location |
|---|---|---|
| Chain runner (outputKey sidecar fix) | Shipped | `server/modules/chain/definition_runner.py` |
| Braindump-to-docs context prompt | Shipped (underspecified) | `server/context/prompts/braindump-to-docs.md` |
| Braindump-to-docs chain definition | Shipped | `server/modules/chain/definitions/braindump-to-docs.json` |
| Port Spec-Doc Template epic | Companion (not yet started) | Separate spec set |
| CLI provider system-prompt handling | Shipped (possibly buggy) | `server/modules/chain/providers/cli_provider.py` |

## Explicitly Out of Scope

- Detailed prompt content (section headings, example content, word-count rules) -- that is the Port Spec-Doc Template epic
- UI rendering of error states when the chain guard fires -- separate UX task
- Retry logic when the generate step fails -- deferred infrastructure per Engineering Discipline
- Changes to chain definition JSON files -- the definitions are correct; the prompt and runner interpretation need fixing
- Structured parsing of review JSON in the runner -- frontend responsibility

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

===END===
