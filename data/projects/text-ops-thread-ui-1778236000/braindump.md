# Text Ops — Thread / Chain UI

## What this is

A purely UI change to how text operations (brainstorm, expand, compress, clarify, simplify, tldr, bullets, style) are displayed in the spec editor. No API changes, no backend changes. The current model replaces the result in place on every op run. The new model shows every result as a card stacked below the previous one, forming a scrollable thread/chain. The output of each op becomes the input to the next. You can scroll up and see every version.

## Current state

Everything lives in `AppComponent` — no sub-components for the editor. Text ops work like this:

1. User clicks an op chip → `runOp(op)` reads `currentSpec().content` → calls `aiSvc[op](content)`
2. Result lands in a single `aiResult` writable signal — each run overwrites the last
3. Template: if `aiResult()` is set, shows diff view or markdown above the original spec; original is hidden behind an `@else`
4. Apply → writes result back to spec content. Dismiss → clears `aiResult`

There is no history. Every op run destroys the previous result. If you brainstorm and then expand the brainstorm, the brainstorm is gone.

## Desired behavior

- First op click pushes a synthetic "original" card (the spec's current content) then pushes the result card below it
- Each subsequent op click reads the last card's text as input and appends a new result card
- The chain scrolls — you can see all prior versions above
- Only the latest card has active op buttons (for continuing the chain)
- Loading state: latest card shows thinking dots, op chips disabled
- Apply: writes last card's text to spec, clears the chain
- Dismiss: clears the chain, spec unchanged
- File switch: clears the chain (it is ephemeral, not persisted)
- Brainstorm follow-up: appends a new brainstorm card to the chain
- Generate specs from brainstorm: uses last card's text, clears chain after

## Data model

Replace the single `aiResult` signal with a signal array of `OpCard`:

```typescript
interface OpCard {
  id: number;        // monotonically increasing, for @for tracking
  op: string;        // 'original' | 'brainstorm' | 'expand' | 'compress' | ...
  opLabel: string;   // display label, e.g. "Brainstorm", "Expand"
  text: string;      // the content of this version
  latencyMs: number | null; // null for the root card
}

opChain = signal<OpCard[]>([]);
```

`aiResult`, `aiLatencyMs`, `activeOp` become `computed()` derived from the last card so all downstream computeds (`isAdditivOp`, `aiOpLabel`, `diffHtmlUnified`) continue to work with minimal changes.

## File-by-file changes

### New: `src/app/utils/paragraph-diff.ts`

Extract the pure functions `computeParagraphDiff` and `escHtml` from the top of `app.component.ts` into a shared utility. Both `AppComponent` and the new card component import from here.

### New: `src/app/components/op-version-card/op-version-card.component.ts`

Standalone component that renders one card in the chain.

**Inputs:**
- `card: OpCard` (required)
- `isFirst: boolean` — the root "original" card, styled differently (no left border, no op badge fill)
- `isLatest: boolean` — only the last card shows op buttons in its footer
- `isLoading: boolean` — loading in progress; shows thinking dots, disables chips
- `previousText: string | null` — used to compute the diff view for non-additive ops
- `brainstormQuestion: string` — controlled from parent
- `copied: boolean`, `billingError: string | null`, `aiError: boolean`, `canGenerateSpecs: boolean`

**Outputs:**
- `opClicked: EventEmitter<string>` — op chip clicked (expand, compress, etc.)
- `styleClicked: EventEmitter<string>` — style preset clicked
- `applyClicked`, `copyClicked`, `dismissClicked`: EventEmitter<void>
- `followupSubmitted: EventEmitter<string>` — brainstorm follow-up question
- `brainstormQuestionChanged: EventEmitter<string>`
- `generateFromBrainstorm: EventEmitter<void>`

**Template structure:**
```
card-header: op badge + latency badge + copy button
card-body:
  if isAdditive (brainstorm / tldr): markdown render of card.text
  else: diff view of previousText → card.text (using computeParagraphDiff)
card-footer (only when isLatest):
  if isLoading: thinking dots + op label
  else: op chip buttons for continuing chain
  if op === 'brainstorm': follow-up input + generate-from-brainstorm button
  Apply / Dismiss action buttons
```

The diff is computed inside the card using `previousText` input — this is correct for the chain model where each diff should be against the immediately preceding version, not always the original spec.

Internal computeds on the card component:
```typescript
parsedCardContent = computed((): SafeHtml => ...)  // markdown
diffHtml = computed((): SafeHtml => ...)            // paragraph diff vs previousText
isAdditive = computed(() => ['brainstorm', 'tldr'].includes(this.card.op))
```

### `app.component.ts`

**Remove:**
- `aiResult` writable signal
- `aiLatencyMs` writable signal
- `activeOp` writable signal
- `diffHtmlUnified` computed
- `parsedAiResult` computed
- `toggleOp()` method
- `computeParagraphDiff` and `escHtml` top-level functions (moved to utils)

**Add:**
- `opChain = signal<OpCard[]>([])`
- `private _nextCardId = 0`
- `private _latestCardText(): string | null` — returns last card's text if chain non-empty, else `currentSpec()?.content ?? null`

**Convert to computed:**
```typescript
activeOp = computed(() => this.opChain().at(-1)?.op ?? null)
aiResult = computed(() => this.opChain().at(-1)?.text ?? null)
aiLatencyMs = computed(() => this.opChain().at(-1)?.latencyMs ?? null)
```

**Rewrite `_runAi`:**
- If `opChain().length === 0`, push an `original` card first
- On success, append the result card
- On error, set `aiError` or `billingError` as before (no card appended on failure)
- After appending, schedule auto-scroll to the last card

**Rewrite `runOp`:**
- Input text comes from `_latestCardText()` not `currentSpec().content`
- Pass `op` and label to `_runAi`
- Remove `toggleOp` call pattern — chips now call `runOp` directly

**Update all `aiResult.set(null)` callsites** → `opChain.set([])`:
- `selectFile()`
- `closeExpanded()`
- `selectProject()`
- `openContext()`
- `dismissResult()`
- `applyResult()` (also reads from `_latestCardText()` instead of `aiResult()`)

**Update `followupBrainstorm`** to read input from `_latestCardText()`.

**Update `generateFromBrainstormResult`** to read from `_latestCardText()` (instead of `this.aiResult()`).

**Add `@ViewChild`** for auto-scroll:
```typescript
@ViewChild('chainContainer') chainContainer?: ElementRef<HTMLElement>;
// after opChain.update(...):
setTimeout(() => {
  this.chainContainer?.nativeElement
    .lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' });
}, 50);
```

**Import `OpVersionCardComponent`** in the component's `imports` array.

### `app.component.html`

**Replace** the entire `@if (activeProject() && aiResult()) { ... } @else { <div class="expanded-body"...> }` block:

```html
<!-- Original spec body (no chain active) -->
@if (opChain().length === 0) {
  <div class="expanded-body markdown-content" [innerHTML]="parsedContent()"></div>
}

<!-- Op chain -->
@if (opChain().length > 0) {
  <div class="op-chain" #chainContainer>
    @for (card of opChain(); track card.id; let i = $index, last = $last) {
      <app-op-version-card
        [card]="card"
        [isFirst]="i === 0"
        [isLatest]="last"
        [isLoading]="last && aiLoading()"
        [previousText]="i > 0 ? opChain()[i - 1].text : null"
        [canGenerateSpecs]="last && card.op === 'brainstorm' && canGenerateSpecs()"
        [brainstormQuestion]="brainstormQuestion()"
        [copied]="copied()"
        [billingError]="last ? billingError() : null"
        [aiError]="last && aiError()"
        (opClicked)="runOp($event)"
        (styleClicked)="runStyle($event)"
        (applyClicked)="applyResult()"
        (copyClicked)="copyResult()"
        (dismissClicked)="dismissResult()"
        (followupSubmitted)="followupBrainstorm($event)"
        (brainstormQuestionChanged)="brainstormQuestion.set($event)"
        (generateFromBrainstorm)="generateFromBrainstormResult()" />
    }
  </div>
}
```

**Simplify the toolbar:** Op chips stay in the toolbar (they trigger/continue the chain). Apply/Copy/Dismiss move to the card footer (inside `OpVersionCardComponent`). Style presets row stays in toolbar unchanged. Remove the `@if (aiResult())` `editor-toolbar-actions` block from the toolbar.

### `styles.css`

New classes to add (all existing classes are kept and reused inside the card template):

```css
.op-chain {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.op-version-card {
  border-left: 3px solid var(--border);
  padding: 24px 0 24px 24px;
  position: relative;
  animation: rise 0.2s ease;
}

.op-version-card--original {
  border-left: none;
  padding-left: 0;
}

.op-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-family: 'Source Sans 3', sans-serif;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-muted);
}

.op-card-badge {
  background: var(--ink);
  color: var(--bg);
  padding: 2px 8px;
  border-radius: 2px;
  font-weight: 600;
  font-size: 10px;
}

.op-card-badge--original {
  background: none;
  border: 1px solid var(--border-dark);
  color: var(--ink);
}

.op-chain-loading {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 16px 0 16px 27px;
  border-left: 3px solid var(--border);
  font-family: 'Source Sans 3', sans-serif;
  font-size: 12px;
  color: var(--ink-muted);
}

.op-card-footer {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
```

## What we are NOT changing

- No API changes
- No backend changes
- No new routes or services
- No change to how ops are called (`aiSvc.expand()`, `aiSvc.brainstorm()`, etc.)
- No change to Apply logic (still writes to spec content + saves to API)
- No change to the undo/redo stack
- No change to the style presets flow
- No change to `generateFromBrainstormResult` logic beyond reading from `_latestCardText()`

## Open questions

Should the chain be preserved if the user collapses and re-expands the same file, or always cleared on file close? Currently the design clears it — the chain is ephemeral and lives only for the duration of a working session on that file.

Should there be a "jump to original" button at the top of a long chain? Once you have 5+ cards it might be useful to quickly dismiss all results.

Should the diff in each card always compare against the immediately previous card, or should there be an option to diff against the original spec? The prior-card diff is more useful for seeing what each individual op changed; the original diff is more useful for seeing total divergence.

Is there a maximum chain length? 10 cards is probably enough before the UX becomes unwieldy. Could add a soft warning at card 8 and a hard stop at 10 that suggests Apply before continuing.
