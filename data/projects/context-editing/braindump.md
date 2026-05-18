Context files (builder.md, principles.md, codebase.md, references.md, quality.md, versions.md) configure the AI generation pipeline — they get injected into prompts as builder profile and principles context. Right now the app displays them read-only in the "Context" section tab. You click a card, it opens in the reader panel, you see rendered markdown. That's it. No way to edit.

The backend already has everything. PUT /api/context/<key> accepts { content: string } and writes to disk via write_context(). GET /api/context/<key> reads it back. The service layer (read_context/write_context) is done. The DTOs (ContextResponse, ContextUpdateRequest) exist. Zero backend work needed.

The frontend needs an edit mode in the reader panel. When viewing a context file, show an "Edit" button. Click it, the rendered markdown swaps to a textarea with the raw markdown. Save persists via PUT, cancel discards. Same mental model as editing a braindump — nothing fancy.

State management: signals only. contextKey tracks which file is open (needed for the PUT URL). contextEditing boolean toggles the view. contextDraft holds textarea content. contextSaving for loading state. All in AppStateService alongside the existing contextContent and contextTitle signals.

ProjectsService needs one new method: updateContext(key, content) → firstValueFrom(this.http.put(...)). Follows the exact same pattern as every other method in the file.

ReaderPanelComponent gets new inputs (isViewingContext, contextEditing, contextDraft, contextSaving) and outputs (editContextClicked, saveContextClicked, cancelContextEdit, contextDraftChange). Template conditionally shows textarea vs rendered markdown. App-v3 template wires the bindings.

The existing openContext() method in AppStateService already fetches content and sets contextContent/contextTitle. Just need to also set contextKey and reset contextEditing. closeExpanded() needs to clear the new signals too.

Styling: monospace textarea, full width, min-height 300px. Save button with ink background, cancel with outline. Match existing modal-textarea pattern from styles.css.

No new components. No new routes. No new API endpoints. Pure frontend wiring of existing backend capability.
