# 🛠️ Task 2: AI Text Operations

**Purpose**: Implement the five primitives that replace chat — rewrite, expand, compress, clarify, generate.

**Effort**: 2 days

**Dependencies**: Task 1 (Editor)

**Parallel With**: Task 5 (Git Integration)

**Blocks**: Task 3 (Spec Bootstrap)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Five AI operations: rewrite, expand, compress, clarify, generate
- Operation bar UI with buttons
- Selection-based operations (transform selected text)
- Backend proxy to Claude CLI or remote API
- Loading states and error handling

### What's NOT Included
- Chat interface — document-first is the point
- Conversation history — operations are stateless
- Custom prompts — predefined operations only (for MVP)

---

## Prerequisites

Before starting:
- Task 1 complete (editor with selection tracking)
- Claude CLI installed (`claude -p "test"` works)
- Express.js for backend proxy

---

## Implementation Steps

### Step 1: Create AI Service

**File**: `src/app/services/ai.service.ts`

**Purpose**: HTTP client for AI operations

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class AiService {
  private baseUrl = 'http://localhost:3100/api/ai/text';

  rewrite(text: string, instruction: string): Observable<{text: string}> {
    return this.http.post<{text: string}>(`${this.baseUrl}/rewrite`, { text, instruction });
  }

  expand(text: string): Observable<{text: string}> {
    return this.rewrite(text, 'Expand with more detail');
  }
  // Similar for compress, clarify, generate
}
```

### Step 2: Create Operation Bar Component

**File**: `src/app/components/operation-bar/operation-bar.component.ts`

**Purpose**: UI for triggering AI operations

**Pattern**:
```typescript
@Component({
  selector: 'app-operation-bar',
  // Floating bar at bottom of editor
  // Shows when text is selected
  // Buttons for each operation
})
export class OperationBarComponent {
  @Input() hasSelection = false;
  @Output() operate = new EventEmitter<{operation: string; instruction?: string}>();
}
```

### Step 3: Create Backend Proxy

**File**: `server.js`

**Purpose**: Express server proxying to Claude CLI

**Pattern**:
```javascript
app.post('/api/ai/text/rewrite', async (req, res) => {
  const { text, instruction } = req.body;
  const prompt = `${instruction}\n\nText:\n${text}`;
  const result = await execClaude(prompt);
  res.json({ text: result });
});
```

### Step 4: Wire Operations to Editor

**File**: `src/app/app.component.ts`

**Purpose**: Connect operation bar to editor selection

**Pattern**:
```typescript
onOperate(event: {operation: string; instruction?: string}) {
  switch (event.operation) {
    case 'rewrite':
      this.aiService.rewrite(this.selectedText, event.instruction)
        .subscribe(response => this.editor.replaceSelection(response.text));
      break;
    // Similar for expand, compress, clarify, generate
  }
}
```

---

## Verification

```bash
# Terminal 1: Start backend
node server.js

# Terminal 2: Start frontend
npm start
```

**Expected Result**:
- [ ] Select text in editor
- [ ] Operation bar appears
- [ ] Click "Expand" — text is replaced with expanded version
- [ ] Click "Compress" — text is replaced with compressed version
- [ ] "Rewrite" opens instruction input, transforms accordingly

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark done
2. Proceed to Task 3: Spec Bootstrap

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking
