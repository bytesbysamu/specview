---
sidebar_position: 3
---

# Architecture -- Port Spec-Doc Template

**Purpose**: Define what to port, what to strip, and what to update in the braindump-to-docs.md context prompt.

**References**: See [Epic](./epic.md) for scope. See [Analysis](./analysis.md) for gap analysis and adaptation decisions.

---

## Overview

One file change: rewrite `server/context/prompts/braindump-to-docs.md` from a skeletal 252-line template to a fully specified ~200-line template adapted from spec-doc's `server.js` (lines 718-998). The template defines 5 file sections with explicit headings, format constraints, and content guidelines. No runner changes, no definition changes, no new files.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Explicit Over Implicit | Every section heading, every format instruction, every content guideline is spelled out. The LLM has no latitude to invent structure. |
| Adapter (context blocks) | The template does not include tech-stack specifics. `builder.md` and `principles.md` context blocks handle domain-specific guidance. The template is the format adapter; the context blocks are the content adapter. |
| Analysis is a filter, not an audit | The analysis template uses the builder-prescribed 5-section format: Problem, Hard Constraints, Open Questions, Dependencies, Out of Scope. No severity tables, no symptom lists, no analogies. Under 40 lines. |
| No preamble | Per Executor Protocol: "generator's response MUST start with `#`". Applied to the LLM's response: it must start with `===FILE: spec-index.md===`. No "Now I have enough context", no reasoning aloud. |

---

## Source Template (spec-doc server.js lines 718-998)

The spec-doc template has these components:

### System instruction header
```
You are a specification document generator following the Constellation documentation guidelines.
```
Adaptation: remove "Constellation documentation guidelines" reference. Replace with: "You are a specification document generator following structured documentation methodology."

### Builder/principles injection
```
## BUILDER CONTEXT
${builderProfile}
## ARCHITECTURE PRINCIPLES (non-negotiable)
${principles}
```
Adaptation: **strip entirely**. Bubls chain injects these as separate context blocks at Step 2. The template must not duplicate them.

### User input section
```
## USER INPUT
${input}
```
Adaptation: **strip entirely**. The chain runner injects user input as the `current_text` parameter. The template is a context block, not the full prompt.

### File templates (the core to port)

#### spec-index.md
- Keep: capability name, one-line description, quick links table, overview section, related documents
- Strip: emoji prefixes in headings (the spec-doc template uses them but existing Bubls projects do not)

#### analysis.md
- **Replace entirely** with builder-prescribed 5-section format:
  - Problem (2-3 sentences)
  - Hard Constraints (bullet list -- check against builder/principles)
  - Open Questions (table: Question / Resolution / Rationale)
  - Dependencies (table: Dependency / Status / Location)
  - Explicitly Out of Scope (bullet list -- the scope knife)
- Drop: severity summary, issue breakdown table, addressed-by column

#### epic.md
- Keep: business value section, scope (covers + does not cover), tasks table, task details, success criteria, non-goals, related documents
- Strip: emoji prefixes, parallel column (simplify table)
- Keep: "Task status is tracked in [Timeline](./timeline.md)" note

#### architecture.md
- Keep: overview, design principles table, component design, execution flow, design decisions table, related documents
- Strip: tech-specific component examples (`FileName.ts`, `ConfigFile.yml`)
- Replace with: generic component references (`File path — Description`)

#### timeline.md
- Keep: progress table, status legend, history table
- Keep: "This is the ONLY place for status tracking" instruction

### Footer instructions
```
Generate ALL 5 files with COMPLETE, detailed content based on the user's input.
- Each file should be substantial (300+ words)
- Tasks should be specific and actionable
- Architecture should include real technical details
- Be specific to the user's input, not generic
```
Adaptation: keep verbatim. Add:
- "Your response MUST start with `===FILE: spec-index.md===`. No preamble."
- "End with `===END===` after the timeline."
- "Do not include conversational text, explanations, or meta-commentary."

---

## Adapted Template Structure

```
[System instruction]
  "You are a specification document generator..."
  "Your response MUST start with ===FILE: spec-index.md==="
  "Do not include preamble or conversational text"
  "Generate exactly 5 files"

===FILE: spec-index.md===
  [frontmatter]
  # [Capability Name]
  > One-line description
  ## Quick Links (table)
  ## Overview (2-3 paragraphs)
  ## Key Decisions (bullet list)
  ## Related Documents

===FILE: analysis.md===
  [frontmatter]
  # Analysis -- [Capability Name]
  **Purpose** + **Date**
  ## Problem (2-3 sentences)
  ## Hard Constraints (bullets)
  ## Open Questions (resolved) (table)
  ## Dependencies (table)
  ## Explicitly Out of Scope (bullets)
  ## Related Documents

===FILE: epic.md===
  [frontmatter]
  # Epic -- [Capability Name]
  **Purpose** + **Source Analysis**
  ## Business Value (2-3 paragraphs)
  ## Scope (covers + does NOT cover)
  ## Tasks (table + details)
  ## Success Criteria
  ## Non-Goals
  ## Related Documents

===FILE: architecture.md===
  [frontmatter]
  # Architecture -- [Capability Name]
  **Purpose** + **References**
  ## Overview
  ## Design Principles (table)
  ## Affected Components / Component Design
  ## Execution Flow (diagram)
  ## Design Decisions (table)
  ## Related Documents

===FILE: timeline.md===
  [frontmatter]
  # Timeline -- [Capability Name]
  **Purpose**: ONLY place for status tracking
  ## Progress (table)
  ## Estimated Effort (table)
  ## Status Legend
  ## History (table)

===END===

[Footer instructions]
  "300+ words per file"
  "Specific and actionable"
  "Real technical details"
  "Not generic"
```

---

## Diff Summary: Current vs Adapted

| Section | Current (Bubls) | Adapted | Change |
|---------|----------------|---------|--------|
| System instruction | 1 line, generic | 4 lines, explicit no-preamble + file-count | Expanded |
| spec-index.md | Skeleton (7 lines) | Full template (15+ lines) | Expanded |
| analysis.md | Severity-table format | Builder-prescribed 5-section format | Replaced |
| epic.md | Skeleton (30 lines) | Full template (50+ lines) with task detail format | Expanded |
| architecture.md | Skeleton (25 lines) | Full template (40+ lines) with component format | Expanded |
| timeline.md | Skeleton (15 lines) | Full template (25+ lines) with estimated effort | Expanded |
| Footer | 4 instructions | 7 instructions (added no-preamble, `===END===`, no-conversational) | Expanded |
| Total lines | ~252 | ~200 (tighter but more explicit) | Restructured |

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Analysis format | Builder-prescribed 5-section | Per `principles.md`: "No severity tables, no symptom lists, no analogies." The old severity-table format contradicts the builder's own validation rules. |
| Emoji in headings | Strip | Existing Bubls projects (chain-runner-fix, etc.) do not use emojis. Convention consistency. |
| Builder/principles in template | Strip | Already injected as separate context blocks by the chain. Duplicating them wastes tokens and risks contradictions if the blocks are updated independently. |
| No-preamble instruction | Add explicit "MUST start with `===FILE:`" | The most common failure mode is the LLM producing conversational preamble before the first file marker. An explicit constraint prevents this. |
| `===END===` marker | Keep | The file parser uses it as a termination signal. Without it, trailing LLM commentary gets appended to the last file. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
- [Timeline](./timeline.md)

===END===
