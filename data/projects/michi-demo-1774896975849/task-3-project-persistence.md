# 🛠️ Task 3: Project Persistence

**Purpose**: Enable saving and loading of project folders through an Express API, with sidebar navigation for switching between files and projects, ensuring no work is lost through auto-save.

**Effort**: 2 days

**Dependencies**: Task 1 (Monaco Editor Integration), Task 2 (AI Text Operations)

**Parallel With**: —

**Blocks**: Task 4 (Bootstrap Flow), Task 5 (Preview Rendering)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Express API endpoints for CRUD operations on projects and files
- File system storage with projects as directories of markdown files
- Sidebar component with project/file tree navigation
- Auto-save with debounce (1 second delay)
- Project switching without data loss

### What's NOT Included
- Authentication/authorization — single-user local tool for MVP
- Cloud sync — local file system only
- Version history — file system is source of truth
- Collaborative editing — out of scope per epic

---

## Prerequisites

Before starting:
- Express server running on port 3100 (from Task 2)
- Angular services pattern established
- Monaco editor integrated and emitting content changes
- Understanding of Node.js `fs/promises` API

---

## Implementation Steps

### Step 1: Define Project Data Structures

**File**: `src/app/models/project.model.ts`

**Purpose**: Type definitions for project and file structures used across frontend and API.

Define interfaces that represent the project hierarchy. A project contains multiple markdown files, and the sidebar needs metadata about each.

**Pattern**:
```typescript
export interface ProjectFile {
  name: string;      // e.g., "epic.md"
  path: string;      // relative path within project
  content?: string;  // loaded on demand
}

export interface Project {
  id: string;        // folder name
  name: string;      // display name
  files: ProjectFile[];
}

export interface ProjectListItem {
  id: string;
  name: string;
  fileCount: number;
}
```

---

### Step 2: Create Projects API Endpoints

**File**: `server.js`

**Purpose**: Express routes for listing, reading, and writing projects and files.

Add routes under `/api/projects`. Each project is a directory in `./projects/`. Files within are markdown documents. The API handles file system operations and returns JSON.

**Pattern**:
```javascript
const fs = require('fs/promises');
const path = require('path');

const PROJECTS_DIR = path.join(__dirname, 'projects');

// Ensure projects directory exists
await fs.mkdir(PROJECTS_DIR, { recursive: true });

// List all projects
app.get('/api/projects', async (req, res) => {
  const entries = await fs.readdir(PROJECTS_DIR, { withFileTypes: true });
  const projects = entries
    .filter(e => e.isDirectory())
    .map(e => ({ id: e.name, name: e.name }));
  res.json(projects);
});

// Get project with file list
app.get('/api/projects/:id', async (req, res) => {
  const projectPath = path.join(PROJECTS_DIR, req.params.id);
  const files = await fs.readdir(projectPath);
  const mdFiles = files.filter(f => f.endsWith('.md'));
  res.json({
    id: req.params.id,
    name: req.params.id,
    files: mdFiles.map(f => ({ name: f, path: f }))
  });
});

// Read file content
app.get('/api/projects/:id/files/:filename', async (req, res) => {
  const filePath = path.join(PROJECTS_DIR, req.params.id, req.params.filename);
  const content = await fs.readFile(filePath, 'utf-8');
  res.json({ content });
});

// Save file content
app.put('/api/projects/:id/files/:filename', async (req, res) => {
  const filePath = path.join(PROJECTS_DIR, req.params.id, req.params.filename);
  await fs.writeFile(filePath, req.body.content, 'utf-8');
  res.json({ success: true });
});

// Create new project
app.post('/api/projects', async (req, res) => {
  const projectPath = path.join(PROJECTS_DIR, req.body.id);
  await fs.mkdir(projectPath, { recursive: true });
  res.json({ id: req.body.id, name: req.body.name || req.body.id });
});
```

**Security Note**: Validate that `req.params.id` and `req.params.filename` don't contain path traversal characters (`..`, `/`).

---

### Step 3: Create Projects Service

**File**: `src/app/services/projects.service.ts`

**Purpose**: Angular service wrapping API calls with proper typing and error handling.

This service manages the current project state and provides methods for all CRUD operations. It maintains the currently selected project and file.

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class ProjectsService {
  private apiUrl = 'http://localhost:3100/api/projects';
  
  currentProject$ = new BehaviorSubject<Project | null>(null);
  currentFile$ = new BehaviorSubject<ProjectFile | null>(null);
  
  async listProjects(): Promise<ProjectListItem[]> {
    const response = await fetch(this.apiUrl);
    return response.json();
  }
  
  async loadProject(id: string): Promise<Project> {
    const response = await fetch(`${this.apiUrl}/${id}`);
    const project = await response.json();
    this.currentProject$.next(project);
    return project;
  }
  
  async loadFile(projectId: string, filename: string): Promise<string> {
    const response = await fetch(`${this.apiUrl}/${projectId}/files/${filename}`);
    const data = await response.json();
    return data.content;
  }
  
  async saveFile(projectId: string, filename: string, content: string): Promise<void> {
    await fetch(`${this.apiUrl}/${projectId}/files/${filename}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
  }
}
```

---

### Step 4: Build Sidebar Component

**File**: `src/app/components/sidebar/sidebar.component.ts`

**Purpose**: Tree navigation showing projects and their files, handling selection state.

The sidebar displays a collapsible tree: projects at the top level, files nested within. Clicking a file loads it into the editor. Visual indicators show the currently selected project and file.

**Pattern**:
```typescript
@Component({
  selector: 'app-sidebar',
  template: `
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>Projects</h3>
        <button (click)="onNewProject()">+</button>
      </div>
      
      <div class="project-list">
        @for (project of projects; track project.id) {
          <div class="project-item" [class.active]="project.id === currentProjectId">
            <div class="project-name" (click)="selectProject(project)">
              {{ project.name }}
            </div>
            
            @if (project.id === currentProjectId && expandedProject) {
              <div class="file-list">
                @for (file of expandedProject.files; track file.path) {
                  <div 
                    class="file-item" 
                    [class.active]="file.path === currentFilePath"
                    (click)="selectFile(file)">
                    {{ file.name }}
                  </div>
                }
              </div>
            }
          </div>
        }
      </div>
    </div>
  `
})
export class SidebarComponent implements OnInit {
  projects: ProjectListItem[] = [];
  expandedProject: Project | null = null;
  currentProjectId: string | null = null;
  currentFilePath: string | null = null;
  
  @Output() fileSelected = new EventEmitter<{projectId: string, file: ProjectFile}>();
  @Output() newProjectRequested = new EventEmitter<void>();
}
```

---

### Step 5: Implement Auto-Save with Debounce

**File**: `src/app/components/editor/editor.component.ts`

**Purpose**: Save changes automatically after user stops typing, preventing data loss.

Use RxJS `debounceTime` to wait 1 second after the last keystroke before triggering save. Track dirty state to show unsaved indicator. Cancel pending saves when switching files.

**Pattern**:
```typescript
export class EditorComponent implements OnInit, OnDestroy {
  private contentChanges$ = new Subject<string>();
  private saveSubscription: Subscription;
  
  isDirty = false;
  isSaving = false;
  
  ngOnInit() {
    this.saveSubscription = this.contentChanges$.pipe(
      tap(() => this.isDirty = true),
      debounceTime(1000),
      filter(() => this.currentProjectId !== null && this.currentFilePath !== null),
      switchMap(content => {
        this.isSaving = true;
        return from(this.projectsService.saveFile(
          this.currentProjectId!,
          this.currentFilePath!,
          content
        ));
      })
    ).subscribe({
      next: () => {
        this.isDirty = false;
        this.isSaving = false;
      },
      error: (err) => {
        console.error('Auto-save failed:', err);
        this.isSaving = false;
        // isDirty remains true to indicate unsaved changes
      }
    });
  }
  
  onContentChange(content: string) {
    this.contentChanges$.next(content);
  }
  
  ngOnDestroy() {
    this.saveSubscription?.unsubscribe();
  }
}
```

---

### Step 6: Wire Up Main Layout

**File**: `src/app/app.component.ts`

**Purpose**: Coordinate sidebar, editor, and state management in the main application shell.

The app component orchestrates the flow: sidebar emits file selection, app loads content, editor displays it, changes flow back through auto-save.

**Pattern**:
```typescript
@Component({
  selector: 'app-root',
  template: `
    <div class="app-layout">
      <app-sidebar 
        (fileSelected)="onFileSelected($event)"
        (newProjectRequested)="showNewProjectModal = true">
      </app-sidebar>
      
      <main class="main-content">
        <app-operation-bar 
          [disabled]="!currentContent"
          (operate)="onOperation($event)">
        </app-operation-bar>
        
        <app-editor
          [content]="currentContent"
          [projectId]="currentProjectId"
          [filePath]="currentFilePath"
          (contentChange)="onContentChange($event)">
        </app-editor>
      </main>
    </div>
  `
})
export class AppComponent {
  currentContent = '';
  currentProjectId: string | null = null;
  currentFilePath: string | null = null;
  
  async onFileSelected(event: {projectId: string, file: ProjectFile}) {
    this.currentProjectId = event.projectId;
    this.currentFilePath = event.file.path;
    this.currentContent = await this.projectsService.loadFile(
      event.projectId, 
      event.file.path
    );
  }
}
```

---

### Step 7: Add Save Status Indicator

**File**: `src/app/components/editor/editor.component.ts` (template update)

**Purpose**: Visual feedback showing save state so users know their work is protected.

Display a subtle indicator in the editor header showing: saved, saving, or unsaved (dirty) state.

**Pattern**:
```html
<div class="editor-header">
  <span class="filename">{{ currentFilePath }}</span>
  <span class="save-status">
    @if (isSaving) {
      <span class="saving">Saving...</span>
    } @else if (isDirty) {
      <span class="unsaved">●</span>
    } @else {
      <span class="saved">✓</span>
    }
  </span>
</div>
```

**CSS**:
```css
.save-status .unsaved { color: #f59e0b; }
.save-status .saving { color: #6b7280; font-size: 0.8em; }
.save-status .saved { color: #10b981; }
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Start the server
npm run api

# 2. Create a test project via API
curl -X POST http://localhost:3100/api/projects \
  -H "Content-Type: application/json" \
  -d '{"id": "test-project", "name": "Test Project"}'

# 3. Create a test file
curl -X PUT http://localhost:3100/api/projects/test-project/files/epic.md \
  -H "Content-Type: application/json" \
  -d '{"content": "# Test Epic\n\nThis is a test."}'

# 4. Verify file was created
ls -la projects/test-project/

# 5. Start frontend
npm start

# 6. Open http://localhost:4201
```

**Expected Result**:
1. Sidebar shows "Test Project"
2. Clicking project expands to show "epic.md"
3. Clicking file loads content into editor
4. Editing content shows "●" indicator
5. After 1 second pause, shows "Saving..." then "✓"
6. Refreshing page and reopening file shows saved content

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 3 as done
2. Proceed to Task 4 (Bootstrap Flow) which depends on project creation

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for file-based storage
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking