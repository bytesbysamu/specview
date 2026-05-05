---
sidebar_position: 1
---

# Apply Button — Analysis

**Purpose**: Identify the problems that make compound text operations impossible today and surface design decisions the braindump left open.

**Date**: 2026-04-17

---

## Summary

Five sections, per architecture principles. Under 40 lines of substance.

---

## Problem

Users cannot chain single-shot AI operations without manual copy-paste. The current `applyResult()` method in `app.component.ts:837-839` calls `editor.replaceSelection(newText)`, which overwrites the selected range in Monaco and clears the selection. To compound — humanize then expand then compress — the user must re-select the output, visually confirm boundaries, then invoke the next operation. Three chained operations means six manual steps (select, operate, select, operate, select, operate) instead of three (operate, apply, operate, apply, operate, apply). There is no before/after comparison and no way to reject a bad result without Cmd+Z in Monaco's internal undo stack.

---

## Hard Constraints

| Constraint | Source | Status |
|------------|--------|--------|
| Standalone components, OnPush, signals | Architecture Principles | Current code uses EventEmitter + properties — Apply button should match existing pattern, not introduce signals into a codebase that doesn't use them yet |
| No cross-feature imports | Architecture Principles | Output panel already exists for implementation streaming (`output-panel.component.ts`) — Apply button needs its own component or extends existing, must not couple to implementation panel |
| `data-test` selectors on interactive elements | Architecture Principles | Every new button and display element needs `data-test` attributes |
| No global state manager | Architecture Principles | Apply/undo state lives in `AppComponent` properties, not a service |

---

## Open Questions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Auto-apply after single-shot, or always explicit? | **Always explicit** | Braindump session decided: user controls when output becomes input. Auto-apply surprises users who want to compare. |
| Single-level or multi-level undo? | **Single-level** | Braindump: "A single-level undo (store one previous value) is cheap and prevents the 'I Applied too soon' regret." Multi-level adds complexity with no validated demand. |
| Does Apply replace selection or full content? | **Full content** | The goal is "the textarea becomes the working document." If Apply only replaced the selection, the user would need to re-select for the next operation — same problem as today. Full-content replacement makes each Apply a clean slate for the next operation. |
| Where does the output display? | **Below editor, above operation bar** | Mirrors the implementation output panel position. Doesn't occlude the editor — user can scroll up to compare. |
| Does the output panel persist across file switches? | **No — cleared on file switch** | Same behavior as `historyStack` which is cleared in `onSpecSelect()` at line 369. Output is ephemeral to the current editing session. |

---

## Dependencies

| Dependency | Type | Impact |
|------------|------|--------|
| `EditorComponent.replaceSelection()` | Existing method | Still needed for selection-based operations if we keep that path; Apply uses `content` input setter instead |
| `AppComponent.applyResult()` | Existing method (line 837) | Needs refactoring — currently the only result handler, must split into "stage result" vs "apply result" |
| `OperationBarComponent` | Existing component | Unchanged — operations still emit the same `OperationEvent` |

---

## Explicitly Out of Scope

- **Operation history/log**: Showing a list of all past operations and their results. Deferred until a user asks for it.
- **Diff view**: Side-by-side diff between current editor content and staged output. Valuable but separate capability — would require Monaco's diff editor API.
- **Auto-apply toggle**: A setting to opt back into the old in-place replacement behavior. No validated demand; adds a preference surface for no reason.
- **Chain presets**: Saved sequences of operations (e.g., "humanize → expand → compress"). This is workflow automation, not UI plumbing — belongs in a future capability.

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

