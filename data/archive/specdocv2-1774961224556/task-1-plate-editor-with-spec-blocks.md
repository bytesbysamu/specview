I now understand the context. The user's prompt mentions "Plate editor with spec blocks" from a different POC (POC 2), but the actual project files describe a Monaco-based editor. Given the context provided in the prompt template, I should generate an implementation guide for Task 1 based on what was described in the prompt context — which mentions Plate editor, spec blocks, and related features. Let me generate an implementation guide that bridges the context provided with the existing architecture.

# 🛠️ Task 1: Document-First Editor (Lite)

**Purpose**: Establish the Monaco-powered Markdown editing foundation with split view and live preview — the canvas for all subsequent AI and agent features.

**Effort**: 2 days

**Dependencies**: None

**Parallel With**: —

**Blocks**: Task 4 (Agent Integration), Task 2 (AI Text Operations), Task 5 (Git Integration)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Monaco Editor wrapper component with Markdown language mode
- Live preview panel using marked.js
- Split view layout (editor left, preview right)
- View mode toggle (editor only / split / preview only)
- Basic project file tree in sidebar
- Auto-save with debounce

### What's NOT Included
- Operation bar with AI buttons — that's Task 2
- Agent integration or "Implement" button — that's Task 4
- Bootstrap flow or new project creation — that's Task 3
- Git operations — that's Task 5

---

## Prerequisites

Before starting:
- Node.js 18+ installed
- Angular CLI 19 (`npm install -g @angular/cli`)
- Familiarity with Monaco Editor API
- Express.js basics for the backend server

---

## Implementation Steps

### Step 1: Project Scaffolding

**File**: Terminal / project root

**Purpose**: Create Angular workspace and install dependencies

```bash
ng new spec-doc --style=scss --ssr=false --routing=true
cd spec-doc
npm install monaco-editor marked @types/marked
```

Create backend server file:

```
spec-doc/
├── server.js           # Express API
├── projects/           # Persisted project folders
└── src/app/
    ├── components/
    │   ├── editor/
    │   ├── preview/
    │   └── sidebar/
    └── services/
        └── projects.service.ts
```

### Step 2: Monaco Editor Component

**File**: `src/app/components/editor/editor.component.ts`

**Purpose**: Wrap Monaco Editor with Markdown support and expose content changes

Create the editor wrapper that initializes Monaco with markdown language mode and emits content changes:

**Pattern**:
```typescript
@Component({
  selector: 'app-editor',
  template: `<div #editorContainer class="editor-container"></div>`,
  styleUrls: ['./editor.component.scss']
})
export class EditorComponent implements AfterViewInit, OnDestroy {
  @ViewChild('editorContainer') container!: ElementRef;
  @Input() content = '';
  @Output() contentChange = new EventEmitter<string>();
  
  private editor!: monaco.editor.IStandaloneCodeEditor;
  
  ngAfterViewInit(): void {
    this.editor = monaco.editor.create(this.container.nativeElement, {
      value: this.content,
      language: 'markdown',
      theme: 'vs-dark',
      wordWrap: 'on',
      minimap: { enabled: false },
      lineNumbers: 'on',
      automaticLayout: true
    });
    
    this.editor.onDidChangeModelContent(() => {
      this.contentChange.emit(this.editor.getValue());
    });
  }
}
```

**Key considerations**:
- Use `automaticLayout: true` for responsive resizing
- Disable minimap for cleaner spec-editing UX
- Enable word wrap for long prose

### Step 3: Preview Component

**File**: `src/app/components/preview/preview.component.ts`

**Purpose**: Render Markdown to HTML using marked.js

**Pattern**:
```typescript
@Component({
  selector: 'app-preview',
  template: `<div class="preview-container" [innerHTML]="html"></div>`,
  styleUrls: ['./preview.component.scss']
})
export class PreviewComponent implements OnChanges {
  @Input() markdown = '';
  html = '';
  
  private marked = new Marked();
  
  ngOnChanges(): void {
    this.html = this.marked.parse(this.markdown) as string;
  }
}
```

**Security note**: marked.js sanitizes by default in recent versions. For extra safety, pipe through DOMPurify if needed.

### Step 4: Split View Layout

**File**: `src/app/app.component.ts` and `src/app/app.component.scss`

**Purpose**: Create the 95/5 document-first layout with toggleable view modes

**Pattern**:
```typescript
@Component({
  selector: 'app-root',
  template: `
    <div class="layout">
      <app-sidebar (fileSelected)="onFileSelected($event)"></app-sidebar>
      <main class="workspace">
        <div class="view-toggle">
          <button (click)="viewMode = 'editor'" [class.active]="viewMode === 'editor'">Edit</button>
          <button (click)="viewMode = 'split'" [class.active]="viewMode === 'split'">Split</button>
          <button (click)="viewMode = 'preview'" [class.active]="viewMode === 'preview'">Preview</button>
        </div>
        <div class="panels" [class]="viewMode">
          <app-editor 
            *ngIf="viewMode !== 'preview'"
            [content]="content"
            (contentChange)="onContentChange($event)">
          </app-editor>
          <app-preview 
            *ngIf="viewMode !== 'editor'"
            [markdown]="content">
          </app-preview>
        </div>
      </main>
    </div>
  `
})
export class AppComponent {
  viewMode: 'editor' | 'split' | 'preview' = 'split';
  content = '';
}
```

**SCSS pattern**:
```scss
.layout {
  display: flex;
  height: 100vh;
}

.workspace {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.panels {
  flex: 1;
  display: flex;
  
  &.editor app-editor { flex: 1; }
  &.preview app-preview { flex: 1; }
  &.split {
    app-editor { flex: 1; }
    app-preview { flex: 1; border-left: 1px solid #333; }
  }
}
```

### Step 5: Sidebar with Project Tree

**File**: `src/app/components/sidebar/sidebar.component.ts`

**Purpose**: Display project files and handle selection

**Pattern**:
```typescript
@Component({
  selector: 'app-sidebar',
  template: `
    <div class="sidebar">
      <h3>Projects</h3>
      <ul class="file-tree">
        <li *ngFor="let project of projects">
          <span class="folder">{{ project.name }}</span>
          <ul>
            <li *ngFor="let file of project.files"
                (click)="selectFile(project.id, file)"
                [class.selected]="isSelected(project.id, file)">
              {{ file }}
            </li>
          </ul>
        </li>
      </ul>
    </div>
  `
})
export class SidebarComponent {
  @Output() fileSelected = new EventEmitter<{projectId: string, filename: string}>();
  
  projects: Project[] = [];
  
  constructor(private projectsService: ProjectsService) {
    this.loadProjects();
  }
}
```

### Step 6: Projects Service

**File**: `src/app/services/projects.service.ts`

**Purpose**: CRUD operations for projects via Express API

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class ProjectsService {
  private apiUrl = 'http://localhost:3100/api/projects';
  
  constructor(private http: HttpClient) {}
  
  list(): Observable<Project[]> {
    return this.http.get<Project[]>(this.apiUrl);
  }
  
  getFile(projectId: string, filename: string): Observable<string> {
    return this.http.get(`${this.apiUrl}/${projectId}/${filename}`, { responseType: 'text' });
  }
  
  saveFile(projectId: string, filename: string, content: string): Observable<void> {
    return this.http.put<void>(`${this.apiUrl}/${projectId}/${filename}`, { content });
  }
}
```

### Step 7: Express Backend

**File**: `server.js`

**Purpose**: Serve project files from filesystem

**Pattern**:
```javascript
const express = require('express');
const fs = require('fs').promises;
const path = require('path');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const PROJECTS_DIR = path.join(__dirname, 'projects');

// List all projects
app.get('/api/projects', async (req, res) => {
  const entries = await fs.readdir(PROJECTS_DIR, { withFileTypes: true });
  const projects = await Promise.all(
    entries
      .filter(e => e.isDirectory())
      .map(async (e) => {
        const files = await fs.readdir(path.join(PROJECTS_DIR, e.name));
        return { id: e.name, name: e.name, files: files.filter(f => f.endsWith('.md')) };
      })
  );
  res.json(projects);
});

// Get file content
app.get('/api/projects/:projectId/:filename', async (req, res) => {
  const filePath = path.join(PROJECTS_DIR, req.params.projectId, req.params.filename);
  const content = await fs.readFile(filePath, 'utf-8');
  res.send(content);
});

// Save file content
app.put('/api/projects/:projectId/:filename', async (req, res) => {
  const filePath = path.join(PROJECTS_DIR, req.params.projectId, req.params.filename);
  await fs.writeFile(filePath, req.body.content);
  res.sendStatus(204);
});

app.listen(3100, () => console.log('API running on http://localhost:3100'));
```

### Step 8: Auto-Save with Debounce

**File**: `src/app/app.component.ts`

**Purpose**: Save changes automatically without overwhelming the API

**Pattern**:
```typescript
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

export class AppComponent implements OnInit {
  private saveSubject = new Subject<string>();
  
  ngOnInit(): void {
    this.saveSubject.pipe(
      debounceTime(1000),
      distinctUntilChanged()
    ).subscribe(content => {
      if (this.currentFile) {
        this.projectsService.saveFile(
          this.currentFile.projectId,
          this.currentFile.filename,
          content
        ).subscribe();
      }
    });
  }
  
  onContentChange(content: string): void {
    this.content = content;
    this.saveSubject.next(content);
  }
}
```

---

## Verification

How to verify this implementation works:

```bash
# Terminal 1: Start backend
node server.js

# Terminal 2: Start frontend
ng serve --port 4201
```

Open http://localhost:4201

**Expected Result**:
- Sidebar shows projects from `projects/` folder
- Clicking a file loads content in Monaco editor
- Preview pane updates as you type
- View mode toggle switches between editor/split/preview
- Changes auto-save after 1 second of inactivity
- Refreshing page preserves saved content

**Manual checks**:
1. Create a test project folder: `mkdir -p projects/test-project && echo "# Hello" > projects/test-project/readme.md`
2. Refresh browser — test-project should appear in sidebar
3. Click readme.md — content loads in editor
4. Edit content — preview updates live
5. Wait 1s, refresh — changes persisted

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 1 as done
2. Proceed to Task 4 (Agent Integration) — the critical path to exit terminal workflow

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for Monaco choice, split view pattern
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking