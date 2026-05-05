# Task 4: Agent Integration

**Purpose**: Connect specs to Claude Code — make documents actionable, not just readable.

**Effort**: 2 days

**Dependencies**: Task 3 (Spec Bootstrap)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- "Implement" button on spec documents
- Context builder (gathers spec files for agent)
- Claude Code invocation with spec context
- Stream output back to UI
- Task execution from timeline

### What's NOT Included
- Full code generation — agent decides what to build
- Inline code editing — specs flow to agent, not reverse
- Multiple agent providers — Claude Code only for MVP

---

## Prerequisites

Before starting:
- Task 3 complete (specs can be generated)
- Claude Code installed and working (`claude` command available)
- Understanding of how Claude Code accepts context via CLAUDE.md

---

## Implementation Steps

### Step 1: Create Agent Service

**File**: `src/app/services/agent.service.ts`

**Purpose**: Interface to Claude Code execution

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class AgentService {
  private baseUrl = 'http://localhost:3100/api/agent';

  execute(context: AgentContext): Observable<StreamEvent> {
    return this.http.post<StreamEvent>(`${this.baseUrl}/execute`, context, {
      // Enable streaming response
    });
  }
}

interface AgentContext {
  task: string;           // Task description
  specs: SpecFile[];      // Relevant spec files
  workingDir: string;     // Where to execute
}

interface SpecFile {
  filename: string;
  content: string;
}
```

### Step 2: Create Backend Agent Endpoint

**File**: `server.js`

**Purpose**: Execute Claude Code with spec context

**Pattern**:
```javascript
app.post('/api/agent/execute', async (req, res) => {
  const { task, specs, workingDir } = req.body;

  // Build context string from specs
  const context = specs.map(s =>
    `## ${s.filename}\n\n${s.content}`
  ).join('\n\n---\n\n');

  // Build prompt with specs as context
  const prompt = `You have the following spec documents:\n\n${context}\n\n---\n\nTask: ${task}`;

  // Execute Claude Code (streaming)
  const process = spawn('claude', ['-p', prompt], {
    cwd: workingDir
  });

  // Stream output back
  process.stdout.on('data', data => {
    res.write(data);
  });

  process.on('close', () => {
    res.end();
  });
});
```

### Step 3: Create Implement Button Component

**File**: `src/app/components/implement-button/implement-button.component.ts`

**Purpose**: UI for triggering agent execution

**Pattern**:
```typescript
@Component({
  selector: 'app-implement-button',
  // Button that appears on spec documents
  // Shows "Implement" with play icon
  // Loading state during execution
  // Output panel for streaming results
})
export class ImplementButtonComponent {
  @Input() spec: SpecFile;
  @Input() relatedSpecs: SpecFile[] = [];

  executing = false;
  output = '';

  async execute() {
    this.executing = true;
    this.output = '';

    // Build context from current spec + related specs
    const context = {
      task: `Implement according to: ${this.spec.filename}`,
      specs: [this.spec, ...this.relatedSpecs],
      workingDir: this.getWorkingDir()
    };

    // Stream output
    this.agentService.execute(context).subscribe(
      event => this.output += event.text,
      error => this.handleError(error),
      () => this.executing = false
    );
  }
}
```

### Step 4: Wire to Editor View

**File**: `src/app/app.component.ts`

**Purpose**: Show implement button when viewing implementation guides

**Pattern**:
```typescript
// In template
@if (isImplementationGuide(currentFile)) {
  <app-implement-button
    [spec]="currentFile"
    [relatedSpecs]="getRelatedSpecs(currentFile)">
  </app-implement-button>
}

// In component
isImplementationGuide(file: SpecFile): boolean {
  return file.filename.startsWith('task-');
}

getRelatedSpecs(taskFile: SpecFile): SpecFile[] {
  // Return epic.md, architecture.md for context
  return this.currentProject.specs.filter(s =>
    ['epic.md', 'architecture.md'].includes(s.filename)
  );
}
```

---

## Verification

How to verify this implementation works:

```bash
# Terminal 1: Start backend
node server.js

# Terminal 2: Start frontend
npm start

# Open a project with implementation guides
# Click "Implement" on task-1-document-first-editor.md
```

**Expected Result**:
- [ ] Implement button appears on task-* files
- [ ] Clicking shows loading state
- [ ] Claude Code output streams to UI
- [ ] Related specs (epic, architecture) are sent as context
- [ ] Agent can read specs and generate appropriate code

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark done
2. Proceed to Task 5: Git Integration

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking
