---
sidebar_position: 2
---

# Epic -- Port Spec-Doc Template

**Purpose**: Define scope and tasks for porting the 5-file generation template from spec-doc's server.js into Bubls' braindump-to-docs.md context prompt.

**Source Analysis**: See [Analysis](./analysis.md) for gap analysis and adaptation decisions.

---

## Business Value

The pipeline comparison proved the gap: spec-doc produces 20K+ chars across 5 structured files with actionable content. Bubls chain produces 1 file (231 chars) for the same braindump when it fails, and matches spec-doc quality when it works (Distribution Experiment). The difference is the prompt content -- 180 lines of explicit instructions vs a skeletal template. Porting the template makes the Bubls chain reliably produce the same quality output AND adds lint + score sidecars that spec-doc does not have. One file change turns Bubls chain into the strictly better pipeline.

This is also the upstream fix for the Chain Output Fix epic: the runner guard catches failures, but the template fix prevents them. Together they form a complete solution: good prompt (prevents most failures) + guard (catches remaining ones).

---

## Scope

### What This Epic Covers

- **Template port**: rewrite `server/context/prompts/braindump-to-docs.md` with the full 5-file template from spec-doc's server.js, adapted for product-agnostic use
- **Analysis format update**: replace the severity-table analysis template with the builder-prescribed 5-section format (Problem, Hard Constraints, Open Questions, Dependencies, Out of Scope)
- **Strip tech-specific content**: remove Angular/Express examples, constellation methodology references, and other domain-specific content from the template
- **Preserve format enforcement**: keep the "300+ words per file" instruction, the "be specific, not generic" instruction, and all section headings
- **Validation**: run the braindump-to-docs chain with 2-3 different braindumps and compare output quality before vs after

### What This Epic Does NOT Cover

- Runner changes (file-marker guard is in Chain Output Fix epic)
- New file types beyond the existing 5
- Changes to builder.md or principles.md context blocks
- Changes to chain definitions
- UI changes

---

## Tasks

**Note**: Task status tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 1 | **Diff spec-doc template vs Bubls template** | None | 0.25 day | High |
| 2 | **Write adapted braindump-to-docs.md** | 1 | 0.5 day | High |
| 3 | **Validate with 3 braindumps** | 2 | 0.5 day | High |

### Task Details

#### Task 1: Diff spec-doc template vs Bubls template

Line-by-line comparison of spec-doc's `server.js` template (lines 718-998) against the current `server/context/prompts/braindump-to-docs.md`. Produce a decision list:

- **Keep**: file markers, section headings, format instructions, word-count enforcement, `===END===` marker
- **Strip**: Angular/Express architecture examples, constellation methodology references, emoji prefixes in headings
- **Update**: analysis template from severity-table format to builder-prescribed 5-section format (Problem, Hard Constraints, Open Questions, Dependencies, Out of Scope)
- **Add**: explicit "no preamble" instruction (per Executor Protocol: "response MUST start with `===FILE:`"), explicit "no conversational text" instruction

#### Task 2: Write adapted braindump-to-docs.md

Rewrite `server/context/prompts/braindump-to-docs.md` with:

1. **System instruction header**: "You are a specification document generator. Your response MUST start with `===FILE: spec-index.md===`. Do not include any preamble, explanation, or conversational text. Generate exactly 5 files."
2. **spec-index.md template**: capability name, one-line description, quick links table, 2-3 paragraph overview, related documents section
3. **analysis.md template**: builder-prescribed 5-section format -- Problem (2-3 sentences), Hard Constraints (bullet list), Open Questions (table with Question / Resolution / Rationale columns), Dependencies (table with Dependency / Status / Location columns), Explicitly Out of Scope (bullet list). Under 40 lines total.
4. **epic.md template**: business value (2-3 paragraphs), scope (covers + does not cover), tasks table (# / Task / Dependencies / Effort / Priority), task details with brief descriptions, success criteria, non-goals, related documents
5. **architecture.md template**: overview paragraph, design principles table, component design per task, execution flow diagram, design decisions table, related documents
6. **timeline.md template**: progress table (# / Task / Status / Notes), status legend, history table
7. **Footer instructions**: "Generate ALL 5 files with COMPLETE, detailed content based on the user's input. Each file should be substantial (300+ words). Tasks should be specific and actionable. Architecture should include real technical details. Be specific to the user's input, not generic."
8. **`===END===` termination marker**

#### Task 3: Validate with 3 braindumps

Run the braindump-to-docs chain with three different braindumps and verify output quality:

1. **Chain Output Fix braindump** (`braindump-chain-output-fix.md`) -- technical bug fix, should produce runner/prompt-specific tasks
2. **Port Spec-Doc Template braindump** (`braindump-port-specdoc-template.md`) -- prompt engineering task, should produce template-specific analysis
3. **A non-technical braindump** -- use a product-idea braindump (e.g., Distribution Experiment) to verify the template works for non-bug-fix braindumps

For each run, check:
- All 5 files present with correct `===FILE:===` markers
- Each file has 300+ words of substantive content
- Analysis uses 5-section format (not severity tables)
- No conversational preamble ("Alright, here's what I'm seeing...")
- No meta-responses about permissions or capabilities
- Tasks are specific and actionable (not placeholders)

---

## Success Criteria

- Bubls braindump-to-docs chain produces 5 structured files with 20K+ total chars (matching spec-doc quality) for all 3 test braindumps
- Analysis documents use the builder-prescribed 5-section format
- No conversational preamble or meta-responses in any test run
- All `===FILE:===` markers present and parseable by `file_parser.py`
- The `===END===` termination marker is present at the end of output
- Template is product-agnostic: no Angular, Express, or constellation-specific content
- Existing chain tests pass without modification

---

## Non-Goals

- Runner changes
- New file types
- Changes to context blocks
- Making the template work without builder.md and principles.md context blocks

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

===END===
