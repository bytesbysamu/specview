---
sidebar_position: 1
---

# Analysis -- Port Spec-Doc Template

**Purpose**: Identify the gap between the spec-doc template and the Bubls template, surface what to keep vs strip, and resolve the adaptation decisions before writing the new prompt.

**Date**: 2026-04-17

---

## Problem

The Bubls `braindump-to-docs.md` context prompt has the right file-marker structure (`===FILE: spec-index.md===` through `===FILE: timeline.md===`) but skeletal section descriptions. Where spec-doc's template says "2-3 paragraphs: what this capability does, why it matters, who benefits" with explicit section headings and word-count enforcement, the Bubls template says the same in abbreviated form without enforcement. The LLM treats the skeletal template as a soft suggestion -- sometimes producing 5 well-structured files, sometimes producing 1 file, sometimes producing a meta-response about what it could do. The spec-doc template's explicitness is the constraint that makes output reliable.

## Hard Constraints

- **One file change** -- the entire fix is updating `server/context/prompts/braindump-to-docs.md`. No runner changes, no definition changes, no new files.
- **Context blocks already injected** -- the Bubls chain definition injects `builder.md` and `principles.md` as separate context blocks at Step 2 (generate). The template must not duplicate content from these blocks.
- **Product-agnostic** -- the template must work for any braindump, not just Angular/Express products. Tech-stack-specific examples from spec-doc's template must be stripped.
- **Analysis format follows builder.md** -- per `principles.md` validation rules, the analysis doc has 5 sections: Problem, Hard Constraints, Open Questions, Dependencies, Explicitly Out of Scope. Under 40 lines. No severity tables, no symptom lists, no analogies. The old spec-doc template uses a severity-table format for analysis; the port must use the builder-prescribed format instead.
- **File markers are exact** -- the `===FILE: filename.md===` format is parsed by `file_parser.py`. Markers must match exactly: `===FILE: spec-index.md===`, `===FILE: analysis.md===`, `===FILE: epic.md===`, `===FILE: architecture.md===`, `===FILE: timeline.md===`.

## Open Questions (resolved)

| Question | Resolution | Rationale |
|---|---|---|
| Port verbatim or adapt? | Adapt: keep structure + section headings + format enforcement; strip tech examples + constellation references. | Bubls chain is product-agnostic; the builder + principles context blocks handle domain specifics. Verbatim port would inject Angular/Express examples into non-Angular braindumps. |
| Keep emojis in section headings? | No. Strip emojis from headings. | The existing Bubls projects (chain-runner-fix, etc.) do not use emojis in headings. Consistent with the codebase convention. |
| Keep the "300+ words per file" instruction? | Yes, keep it. | This is the primary output-quality constraint. Without it, the LLM produces skeletal 50-word files. With it, each file is substantive enough to be actionable. |
| What analysis format to use? | Builder-prescribed 5-section format (Problem, Hard Constraints, Open Questions, Dependencies, Out of Scope). | Per `principles.md` validation rules: "Five sections... Under 40 lines total. No severity tables, no symptom lists." The old spec-doc template uses severity tables; the port updates to the builder convention. |
| Should the template include the `===END===` marker? | Yes, at the very end after timeline.md. | The file parser uses `===END===` as a termination signal. Omitting it can cause the parser to include trailing LLM commentary as part of the last file. |

## Dependencies

| Dependency | Status | Location |
|---|---|---|
| Spec-doc server.js template (source) | Shipped (stable) | `/projects/2026/spec-doc/server.js` lines 718-998 |
| Bubls braindump-to-docs prompt (target) | Shipped (underspecified) | `server/context/prompts/braindump-to-docs.md` |
| Builder profile context block | Shipped | `server/context/prompts/builder.md` |
| Principles context block | Shipped | `server/context/prompts/principles.md` |
| File parser | Shipped | `server/modules/chain/file_parser.py` |
| Chain Output Fix epic (runner guard) | Companion | Separate spec set |

## Explicitly Out of Scope

- Runner changes (file-marker guard is in the Chain Output Fix epic)
- New context blocks or chain definition changes
- Changes to builder.md or principles.md
- Adding new file types beyond the 5-file set
- Changing the file parser
- UI changes

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

===END===
