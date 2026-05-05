---
sidebar_position: 3
---

# Apply Button — Solution Architecture

**Purpose**: Technical design for compound text operations via result staging and Apply.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

This capability adds one new component and refactors one method. The existing data flow is:

```
Operation Bar → AppComponent.onOperate() → AiService → AppComponent.applyResult() → Editor.replaceSelection()
```

The new flow splits `applyResult()` into two steps — stage and apply:

```
Operation Bar → AppComponent.onOperate() → AiService → AppComponent.stageResult()
                                                              ↓
                                                     TextOutputComponent (displays result)
                                                              ↓ [user taps Apply]
                                                     AppComponent.applyToEditor()
                                                              ↓
                                                     this.content = stagedOutput
                                                              ↓
                                                     Editor [content] binding updates
```

Iterate, GenerateSpec, and Revert bypass the staging flow entirely — they set `this.content` directly as they do today. This is intentional: those operations already manage their own history stack and full-content replacement. The Apply button only governs single-shot operations.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Standalone components, OnPush | `TextOutputComponent` is standalone with `ChangeDetectionStrategy.OnPush`. Inputs/outputs only — no injected services. |
| No cross-feature imports | Text output panel is its own component, does not import from `output-panel` (implementation streaming) despite visual similarity. Shared styles are duplicated — two components is cheaper than a premature abstraction. |
| State via component properties | `stagedOutput`, `preApplyContent` are properties on `AppComponent`, matching `content`, `selectedText`, `historyStack`. No service, no signal. |
| `data-test` selectors | Every interactive element in the new component gets a `data-test` attribute. |
| Explicit over implicit | Apply is always explicit — no auto-apply, no settings toggle. The user taps a button. |

---

## Component Design

### Task 1: Result staging state

**Purpose**: Hold the AI result separately from editor content until the user explicitly applies it.

**Components**:
- `src/app/app.component.ts` — add `stagedOutput: string = ''` and `preApplyContent: string = ''` properties

**State transitions**:

| Event | `stagedOutput` | `preApplyContent` | `content` |
|-------|---------------|-------------------|-----------|
| AI operation completes | Set to result | Unchanged | Unchanged |
| User taps Apply | Cleared | Set to current `content` | Set to `stagedOutput` |
| User taps Undo Apply | Unchanged | Cleared | Set to `preApplyContent` |
| User taps Dismiss | Cleared | Unchanged | Unchanged |
| User switches file | Cleared | Cleared | Set to new file content |
| New AI operation starts | Cleared (previous result discarded) | Unchanged | Unchanged |

### Task 2: TextOutputComponent

**Purpose**: Display staged AI result with Apply/Dismiss actions.

**Components**:
- `src/app/components/text-output/text-output.component.ts` — new standalone component

**Interface**:
```typescript
@Input() output: string = '';
@Input() loading: boolean = false;
@Output() apply = new EventEmitter<void>();
@Output() dismiss = new EventEmitter<void>();
```

**Template structure**:
```
div.text-output-panel [data-test="text-output-panel"]
├── div.panel-header
│   ├── span "AI Output"
│   ├── button.apply-btn [data-test="apply-output"] "✓ Apply"
│   ├── button.dismiss-btn [data-test="dismiss-output"] "✕"
│   └── span.spinner (*ngIf="loading")
└── div.panel-content [data-test="staged-output-content"]
    └── pre {{ output }}
```

**Styling**: Dark theme consistent with operation bar (`#252526` background). Max height `40vh` with `overflow-y: auto`. Apply button uses `#238636` (green, matches existing toast success color). Dismiss is subtle (`#3c3c3c` background).

**Patterns**: Standalone component with `ChangeDetectionStrategy.OnPush`. No services injected. Pure display + event emission.

### Task 3: Wire operations to staging

**Purpose**: Redirect single-shot AI results from in-place replacement to the staging panel.

**Components**:
- `src/app/app.component.ts` — refactor `applyResult()` method

**Current** (`app.component.ts:837-839`):
```typescript
private applyResult(newText: string): void {
  this.loading = false;
  this.editor.replaceSelection(newText);
}
```

**New**:
```typescript
private stageResult(newText: string): void {
  this.loading = false;
  this.stagedOutput = newText;
}
```

All five single-shot `subscribe.next` callbacks call `applyResult()` — renaming + changing the body redirects all of them. No changes to the `onOperate()` switch cases for iterate/revert/generateSpec.

### Task 4: Apply action

**Purpose**: Promote staged output into the editor.

**Components**:
- `src/app/app.component.ts` — add `applyToEditor()` method

**Method**:
```typescript
applyToEditor(): void {
  this.preApplyContent = this.content;
  this.content = this.stagedOutput;
  this.stagedOutput = '';
  this.onContentChange(this.content);  // triggers auto-save
}
```

**Template binding**: `(apply)="applyToEditor()"` on the `<app-text-output>` element.

### Task 5: Undo Apply

**Purpose**: Restore editor content to pre-Apply state.

**Components**:
- `src/app/app.component.ts` — add `undoApply()` method
- `src/app/components/operation-bar/operation-bar.component.ts` — add Undo Apply button

**Method**:
```typescript
undoApply(): void {
  if (this.preApplyContent) {
    this.content = this.preApplyContent;
    this.preApplyContent = '';
    this.onContentChange(this.content);
  }
}
```

**Operation bar addition**: New input `canUndoApply: boolean`, new button styled like Revert (amber border, `#f0a050` accent). Emits a new `OperationEvent` with operation `'undoApply'` or a dedicated `@Output() undoApply = new EventEmitter<void>()`.

**Design decision**: Undo Apply lives in the operation bar rather than the text output panel because the output panel is hidden after Apply. The user needs the undo button visible while editing the promoted content.

---

## Execution Flow

```
[Phase 1 — Parallel]
   Task 1 (state props)  ──→  Task 3 (wire staging)
   Task 2 (component)    ──→  Task 4 (apply action)
                                    │
[Phase 2 — Sequential]             ▼
                              Task 5 (undo)
                                    │
                                    ▼
                              Task 6 (tests + data-test)
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Separate component vs. reuse OutputPanelComponent | **Separate** | OutputPanel is wired to SSE streaming for implementation tasks — it has `running`, `success`, `files`, `taskName` inputs and accept/retry outputs. Text output needs none of that. Two small components > one overloaded component. |
| Plain `<pre>` vs. rendered markdown in output | **Plain `<pre>`** | The output is working text, not a finished document. Pre-formatted text lets the user see exactly what they're applying. Rendered markdown hides whitespace and formatting characters. If users want to preview, they can Apply and check the preview pane. |
| Apply replaces full content vs. selection | **Full content** | The braindump specifies "the output replaces the textarea content." Full replacement makes every operation read the entire document, which is what compound workflows need. Selection-level replacement would require re-selecting after each Apply — same friction as today. |
| Undo in operation bar vs. output panel | **Operation bar** | The output panel is hidden after Apply. Undo must be accessible while the user works with the promoted content. Operation bar is always visible. Styled like Revert to signal "go back" semantics. |
| Clear staged output on new operation | **Yes** | Starting a new AI operation means the user has moved on. Keeping stale output from a previous operation alongside the new loading state would confuse. Clear `stagedOutput` when `loading` flips to `true`. |
| `stagedOutput` state in AppComponent vs. dedicated service | **AppComponent property** | Matches existing pattern — `content`, `selectedText`, `historyStack`, `baseSpecContent` are all AppComponent properties. No service needed for two strings. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

