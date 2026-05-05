# Task 1: Document-First Editor

**Purpose**: Build the foundation — a browser-based Markdown editor where users write directly in the document, not in a chat interface.

**Effort**: 3 days

**Dependencies**: None

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Monaco Editor integration for Markdown editing
- marked.js preview with live rendering
- Split view (editor | preview) like VS Code
- View mode toggle (editor only, split, preview only)
- Basic file state management

### What's NOT Included
- AI operations — see Task 2
- Multiple files/projects — see Task 3
- Git integration — see Task 5

---

## Prerequisites

Before starting:
- Node.js 18+ and npm installed
- Angular CLI (`npm install -g @angular/cli`)
- Basic understanding of Angular components

---

## Implementation Steps

### Step 1: Create Editor Component

**File**: `src/app/components/editor/editor.component.ts`

**Purpose**: Wrap Monaco Editor for Markdown editing

**Pattern**:
```typescript
@Component({
  selector: 'app-editor',
  standalone: true,
  // Monaco Editor with markdown language
})
export class EditorComponent {
  @Input() content = '';
  @Output() contentChange = new EventEmitter<string>();
  @Output() selectionChange = new EventEmitter<{text: string; range: any}>();

  // Initialize Monaco with markdown language mode
  // Emit changes on edit
  // Track selection for AI operations
}
```

### Step 2: Create Preview Component

**File**: `src/app/components/preview/preview.component.ts`

**Purpose**: Render Markdown to HTML using marked.js

**Pattern**:
```typescript
@Component({
  selector: 'app-preview',
  // Render markdown to HTML
})
export class PreviewComponent {
  @Input() markdown = '';

  // Use marked.parse() to render
  // Sanitize output for security
  // Apply syntax highlighting for code blocks
}
```

### Step 3: Create Split View Layout

**File**: `src/app/app.component.ts`

**Purpose**: Combine editor and preview in split view

**Pattern**:
```typescript
// View modes: 'editor' | 'split' | 'preview'
// Toggle buttons in toolbar
// Flexbox layout for split panes
// Editor on left, preview on right
```

### Step 4: Add View Mode Toggle

**File**: `src/app/app.component.ts` (toolbar section)

**Purpose**: Allow switching between view modes

**Pattern**:
```html
<div class="view-toggle">
  <button (click)="viewMode = 'editor'">Editor</button>
  <button (click)="viewMode = 'split'">Split</button>
  <button (click)="viewMode = 'preview'">Preview</button>
</div>
```

---

## Verification

How to verify this implementation works:

```bash
npm start
# Open http://localhost:4200
```

**Expected Result**:
- [ ] Monaco editor loads with Markdown syntax highlighting
- [ ] Preview renders Markdown in real-time
- [ ] View toggle switches between modes
- [ ] Selection in editor tracked for later AI operations

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark done
2. Proceed to Task 2: AI Text Operations

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking
