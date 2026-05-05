---
sidebar_position: 2
---

# Apply Button — Epic

**Purpose**: Define scope and tasks for compound text operations via Apply button.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed and design decisions.

---

## Business Value

Every single-shot AI operation today is terminal — the result lands in the editor and the interaction ends. Users who want to refine text through multiple passes (humanize → formalize → compress) must manually copy output, clear their workspace, paste, and re-invoke. This friction means the five text operations are used in isolation rather than composed, which undercuts Spec Doc's value proposition as a document workbench.

The Apply button turns single-shot operations into a composable pipeline with one new UI element. The output stages in a visible panel; the user decides when to promote it. This makes the editor a working document that accumulates refinement rather than a one-shot input field. Combined with single-level undo, it removes the fear of committing to a bad result.

The implementation is small (one new component, one refactored method, two new state properties) but the behavioral change is significant: Spec Doc becomes a tool where you build text iteratively, not just transform it once.

---

## Scope

### What This Epic Covers

- Staging AI results in a visible output panel instead of immediate in-place replacement
- "Apply" button that promotes staged output into the editor as full content replacement
- Single-level undo that restores the editor to its pre-Apply state
- Clearing staged output on file switch or new operation
- `data-test` selectors on all new interactive elements

### What This Epic Does NOT Cover

- Multi-level undo history (single-level only)
- Diff view between editor and output
- Auto-apply mode or user preference toggle
- Chain presets / saved operation sequences
- Changes to Iterate, GenerateSpec, or Revert flows (these already manage full-content replacement and history)
- Changes to the AI service layer or backend endpoints

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Add result staging state to AppComponent** | None | 2 | 2h | High |
| 2 | **Create text output panel component** | None | 1 | 3h | High |
| 3 | **Wire operations to stage instead of replace** | 1 | — | 1h | High |
| 4 | **Implement Apply action** | 1, 2 | — | 2h | High |
| 5 | **Implement single-level Undo** | 4 | — | 1h | Medium |
| 6 | **Add data-test selectors and component tests** | 2, 4, 5 | — | 2h | Medium |

### Task Details

#### Task 1: Add result staging state to AppComponent

Add two new properties to `AppComponent`: `stagedOutput: string` (the AI result waiting to be applied) and `preApplyContent: string` (the editor content before the last Apply, for undo). Add a `clearStagedOutput()` method. Call it in `onSpecSelect()` alongside the existing `historyStack = []` reset. These properties are component-level state — no service, no signal, just properties matching the existing pattern (`content`, `selectedText`, `loading`, etc.).

#### Task 2: Create text output panel component

Create `src/app/components/text-output/text-output.component.ts` — a standalone component that displays the staged AI result as read-only rendered markdown. Inputs: `output: string`, `loading: boolean`. Outputs: `apply: EventEmitter<void>`, `dismiss: EventEmitter<void>`. Renders a scrollable text area with the output content, an "Apply" button, a "Dismiss" button, and a loading spinner when `loading` is true. Positioned in the main layout between the editor/preview area and the operation bar. Only visible when `stagedOutput` is non-empty or `loading` is true. Styled consistently with the existing dark theme (`#252526` background, `#d4d4d4` text, `#007acc` accent). Max height ~40% of viewport with scroll overflow.

#### Task 3: Wire operations to stage instead of replace

Refactor `AppComponent.applyResult()` (currently at line 837) to write to `stagedOutput` instead of calling `editor.replaceSelection()`. The five single-shot operations (rewrite, expand, compress, clarify, generate) all flow through `applyResult()` — changing this one method redirects all of them to the staging panel. The Iterate, GenerateSpec, and Revert operations bypass `applyResult()` and set `this.content` directly — leave them unchanged.

#### Task 4: Implement Apply action

Handle the `apply` event from the text output panel. Store current `this.content` in `preApplyContent`. Set `this.content = this.stagedOutput`. Clear `stagedOutput`. The editor picks up the new content via its `[content]` input binding. Auto-save triggers via the existing `onContentChange` → `saveSubject` debounce path. After Apply, the user's next operation reads from the promoted content.

#### Task 5: Implement single-level Undo

Add an "Undo Apply" button (visible only when `preApplyContent` is non-empty). On click: set `this.content = this.preApplyContent`, clear `preApplyContent`. This is a single-level undo — applying again overwrites the undo slot. The undo button can live in the operation bar (alongside Revert) or in the text output panel header. Clears on file switch.

#### Task 6: Add data-test selectors and component tests

Add `data-test="apply-output"` to the Apply button, `data-test="dismiss-output"` to Dismiss, `data-test="undo-apply"` to Undo, `data-test="text-output-panel"` to the panel container, `data-test="staged-output-content"` to the output text area. Write TestBed tests for the text output component: panel visibility, apply emits, dismiss emits, loading state. Write tests for AppComponent: staged output flow, apply promotes content, undo restores content, file switch clears state.

---

## Success Criteria

- A user can run Rewrite on selected text, see the result in the output panel, then tap Apply to promote it into the editor
- A user can run Expand on the full (now-promoted) content, see the expanded result, and Apply again — compounding two operations
- Tapping Undo after Apply restores the editor to its pre-Apply content
- Switching files clears staged output and undo state
- Iterate, GenerateSpec, and Revert continue to work exactly as they do today (full-content replacement, history stack)
- All new interactive elements have `data-test` selectors

---

## Non-Goals

- Multi-level undo (one level is sufficient until validated otherwise)
- Diff view or side-by-side comparison
- Persisting staged output to the backend
- Changing the AI service or backend endpoints
- Modifying chain mode behavior (iterate/generateSpec/revert)

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

