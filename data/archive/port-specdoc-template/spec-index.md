---
sidebar_position: 0
---

# Port Spec-Doc 5-File Template into Bubls Chain

> Copy the proven 5-file generation template from spec-doc's server.js into Bubls' braindump-to-docs.md context prompt, stripping tech-specific examples while preserving the structure that reliably produces file-marker output.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [Analysis](./analysis.md) | Gap analysis between spec-doc and Bubls templates, adaptation decisions |
| [Epic](./epic.md) | Scope, tasks, success criteria |
| [Architecture](./architecture.md) | What to port, what to strip, what to keep |
| [Timeline](./timeline.md) | Status tracking |

## Overview

The spec-doc `server.js` generate-spec endpoint (lines 718-998) contains a 180-line prompt template that reliably produces 5 named files with `===FILE:===` markers: spec-index.md, analysis.md, epic.md, architecture.md, and timeline.md. Each file template includes section headings, format instructions, and content guidelines that constrain the LLM to produce structured output. The Bubls chain uses an underspecified version of this template in `server/context/prompts/braindump-to-docs.md` -- same file markers, but skeletal section descriptions that give the LLM too much latitude. The result: spec-doc produces 20K+ chars across 5 structured files; Bubls sometimes produces 1 file (231 chars) for the same braindump.

When the Bubls chain does work (as demonstrated with the Distribution Experiment braindump), it matches spec-doc quality AND adds lint + score sidecars that spec-doc does not have. The prompt content is the only difference. Porting the template turns Bubls chain into the strictly better pipeline.

The port is not verbatim. The spec-doc template references constellation methodology by name and includes Angular/Express-specific architecture examples. Bubls chain should be product-agnostic -- the template needs the file-marker structure and section headings but not the tech-stack examples. The builder and principles context blocks (already injected by the chain) handle domain-specific guidance.

## Key Decisions

- **Port structure, strip examples** -- keep all file markers, section headings, and format instructions; remove Angular/Express-specific architecture examples and constellation-specific language
- **Let context blocks handle domain specifics** -- the Bubls chain injects `builder.md` and `principles.md` as separate context blocks; the template should not duplicate their content
- **Keep the 300+ words per file instruction** -- this is the single most important constraint that prevents the LLM from producing skeletal output
- **Keep the analysis format from builder.md** -- the analysis section uses the 5-section format (Problem, Hard Constraints, Open Questions, Dependencies, Out of Scope) per the builder's validation rules, not the severity-table format from the old template

## Related Documents

- [Analysis](./analysis.md) -- gap analysis
- [Epic](./epic.md) -- scope and tasks
- [Architecture](./architecture.md) -- what to port, what to strip
- [Timeline](./timeline.md) -- status tracking
- [Chain Output Fix](../chain-output-fix-GUI/spec-index.md) -- companion epic for runner guard

===END===
