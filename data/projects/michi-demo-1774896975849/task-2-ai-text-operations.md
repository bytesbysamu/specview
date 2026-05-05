# 🛠️ Task 2: AI Text Operations

**Purpose**: Transform the Monaco editor from a passive text editor into an AI-native workspace by implementing text operations (rewrite, expand, compress, clarify) that stream Claude responses directly into the document.

**Effort**: 2 days

**Dependencies**: Task 1 (Monaco Editor Integration) must be complete

**Parallel With**: —

**Blocks**: Task 3 (Document Preview), Task 4 (Project Bootstrap)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Operation bar component with four AI buttons
- Text selection detection and full-document fallback
- Streaming API integration with Claude CLI backend
- Real-time text replacement as response streams in
- Loading states and error handling

### What's NOT Included
- Custom operation instructions — deferred to future iteration
- Undo/redo integration — Monaco handles this automatically
- Operation history/logging — not in MVP scope

---

## Prerequisites

Before starting:
- Monaco editor component functioning (Task 1 complete)
- Claude CLI installed and working (`claude -p "test"` returns response)
- Express server running on port 3100
- Understanding of Angular signals and RxJS observables

---

## Implementation Steps

### Step 1: Create AI Service

**File**: `src/app/services/ai.service.ts`

**Purpose**: Centralize all AI backend communication with streaming support

The service handles HTTP requests to the Express backend and processes Server-Sent Events (SSE) for streaming responses. Each operation type maps to an instruction template.

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class AiService {
  private baseUrl = 'http://localhost:3100/api/ai';

  // Operation templates
  private operations = {
    rewrite: (instruction: string) => `Rewrite this text: ${instruction}`,
    expand: () => 'Expand this text with more detail and explanation',
    compress: () => 'Make this text more concise while preserving meaning',
    clarify: () => 'Rewrite this text to be clearer and easier to understand'
  };

  streamOperation(operation: string, text: string, instruction?: string): Observable<string> {
    // Returns observable that emits chunks as they arrive
    // Uses EventSource or fetch with ReadableStream
  }
}
```

### Step 2: Add Streaming Endpoint to Express Server

**File**: `server.js`

**Purpose**: Proxy AI requests to Claude CLI with streaming response

The endpoint receives operation requests, constructs the Claude CLI command, and streams output back to the client using SSE format.

**Pattern**:
```javascript
app.post('/api/ai/text/rewrite', async (req, res) => {
  const { text, instruction } = req.body;
  
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const prompt = `${instruction}\n\nText to transform:\n${text}`;
  
  // Spawn claude CLI with streaming
  const claude = spawn('claude', ['-p', prompt, '--no-input']);
  
  claude.stdout.on('data', (chunk) => {
    res.write(`data: ${JSON.stringify({ text: chunk.toString() })}\n\n`);
  });
  
  claude.on('close', () => {
    res.write('data: [DONE]\n\n');
    res.end();
  });
});
```

### Step 3: Create Operation Bar Component

**File**: `src/app/components/operation-bar/operation-bar.component.ts`

**Purpose**: UI for triggering AI operations on selected or full text

The component displays four operation buttons, detects text selection from the editor, and orchestrates the transform flow.

**Pattern**:
```typescript
@Component({
  selector: 'app-operation-bar',
  template: `
    <div class="operation-bar">
      @for (op of operations; track op.id) {
        <button 
          (click)="executeOperation(op.id)"
          [disabled]="isProcessing()">
          {{ op.label }}
        </button>
      }
    </div>
  `
})
export class OperationBarComponent {
  @Input() editor!: monaco.editor.IStandaloneCodeEditor;
  
  operations = [
    { id: 'rewrite', label: 'Rewrite' },
    { id: 'expand', label: 'Expand' },
    { id: 'compress', label: 'Compress' },
    { id: 'clarify', label: 'Clarify' }
  ];
  
  isProcessing = signal(false);

  executeOperation(opId: string) {
    const selection = this.editor.getSelection();
    const text = selection 
      ? this.editor.getModel()?.getValueInRange(selection)
      : this.editor.getValue();
    // Stream and replace
  }
}
```

### Step 4: Implement Streaming Text Replacement

**File**: `src/app/components/operation-bar/operation-bar.component.ts`

**Purpose**: Replace selected text progressively as AI response streams in

This creates the "AI typing" effect where users see the transformation happen in real-time. The editor selection is replaced with an empty string initially, then text is inserted character-by-character or chunk-by-chunk.

**Pattern**:
```typescript
private streamReplace(selection: monaco.Selection, operation: string, text: string) {
  this.isProcessing.set(true);
  
  // Store original for potential undo
  const model = this.editor.getModel();
  
  // Clear selection, track insert position
  this.editor.executeEdits('ai-operation', [{
    range: selection,
    text: '',
    forceMoveMarkers: true
  }]);
  
  let insertPosition = selection.getStartPosition();
  
  this.aiService.streamOperation(operation, text).subscribe({
    next: (chunk) => {
      this.editor.executeEdits('ai-operation', [{
        range: new monaco.Range(
          insertPosition.lineNumber,
          insertPosition.column,
          insertPosition.lineNumber,
          insertPosition.column
        ),
        text: chunk
      }]);
      // Update insert position for next chunk
      insertPosition = this.editor.getPosition()!;
    },
    complete: () => this.isProcessing.set(false),
    error: () => this.isProcessing.set(false)
  });
}
```

### Step 5: Add Loading and Error States

**File**: `src/app/components/operation-bar/operation-bar.component.ts`

**Purpose**: Visual feedback during AI operations

Users need to know when an operation is in progress and if something fails. Disable buttons during processing and show error toasts on failure.

**Pattern**:
```typescript
template: `
  <div class="operation-bar">
    @for (op of operations; track op.id) {
      <button 
        (click)="executeOperation(op.id)"
        [disabled]="isProcessing()"
        [class.loading]="isProcessing() && activeOp() === op.id">
        @if (isProcessing() && activeOp() === op.id) {
          <span class="spinner"></span>
        }
        {{ op.label }}
      </button>
    }
  </div>
  @if (error()) {
    <div class="error-toast">{{ error() }}</div>
  }
`
```

### Step 6: Wire Components Together

**File**: `src/app/app.component.ts`

**Purpose**: Connect editor instance to operation bar

The parent component passes the Monaco editor instance to the operation bar so it can read selections and write transformations.

**Pattern**:
```typescript
template: `
  <app-sidebar />
  <main>
    <app-operation-bar [editor]="editorComponent.editor" />
    <app-editor #editorComponent [content]="currentDocument()" />
  </main>
`
```

---

## Verification

How to verify this implementation works:

```bash
# Terminal 1: Start backend
npm run api

# Terminal 2: Start frontend
npm start

# Open browser to http://localhost:4201
```

**Test Sequence**:
1. Type or paste text into the editor
2. Select a portion of text
3. Click "Expand" — selected text should be replaced with expanded version streaming in
4. Click "Compress" on full document (no selection) — entire content transforms
5. Verify undo (Cmd+Z) restores previous state

**Expected Result**: 
- Buttons disable during operation
- Text streams in visibly (not all at once)
- Original text is replaced, not appended
- No console errors

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 2 done
2. Proceed to Task 3 (Document Preview) — preview will show transformed content
3. Consider adding keyboard shortcuts (Cmd+Shift+R for rewrite, etc.)

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for document-as-interface
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking