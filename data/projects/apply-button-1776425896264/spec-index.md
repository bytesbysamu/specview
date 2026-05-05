---
sidebar_position: 0
---

# Apply Button — Compound Text Operations

> Promote AI output into the editor with one tap so operations compound on refined text.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [Analysis](./analysis.md) | Problems driving this capability |
| [Epic](./epic.md) | Scope, tasks, success criteria |
| [Architecture](./architecture.md) | Technical design |
| [Timeline](./timeline.md) | Status tracking |

## Overview

Spec Doc ships with five single-shot text operations (Rewrite, Expand, Compress, Clarify, Generate) and three chain modes (Iterate, GenerateSpec, Revert). Single-shot operations currently replace the selected text in-place via `editor.replaceSelection()` — the AI result overwrites the selection in Monaco and the user moves on. This works for one-shot edits but breaks down the moment a user wants to compose operations: humanize a paragraph, then expand it, then compress it. Each step requires re-selecting the output, and there is no way to compare before and after or undo a bad application.

The Apply Button capability introduces a result staging area between the AI backend and the Monaco editor. Instead of replacing the selection immediately, single-shot operations write their output to a visible output panel. The user reads the result, and if satisfied, taps "Apply" to promote the output into the editor content. The editor becomes the working document: every Apply overwrites its content with the latest output, every subsequent operation reads from it. A single-level undo stores the pre-Apply state so users can recover from a premature promotion.

This is the difference between a tool that does one thing per click and a workbench that builds on itself. The Apply button makes compounding a single tap instead of a copy-paste ritual.

## Related Documents

- [Analysis](./analysis.md)
- [Epic](./epic.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

