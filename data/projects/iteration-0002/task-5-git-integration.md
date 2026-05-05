# Task 5: Git Integration

**Purpose**: Version specs alongside code — MD files as source code.

**Effort**: 1 day

**Dependencies**: Task 1 (Document-First Editor)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Save specs to git repository
- Export project to folder on disk
- Initialize git repo for new projects
- Basic commit workflow (save = commit)
- Push to GitHub remote

### What's NOT Included
- Branch management — MVP is single branch
- Merge conflict resolution — manual in VS Code
- Pull/sync from remote — export only for MVP
- Git history viewer — use native git tools

---

## Prerequisites

Before starting:
- Task 1 complete (editor working)
- Git installed and configured (`git` command available)
- Understanding of basic git workflow

---

## Implementation Steps

### Step 1: Create Git Service

**File**: `src/app/services/git.service.ts`

**Purpose**: Interface to git operations

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class GitService {
  private baseUrl = 'http://localhost:3100/api/git';

  init(projectPath: string): Observable<{success: boolean}> {
    return this.http.post<{success: boolean}>(`${this.baseUrl}/init`, { path: projectPath });
  }

  commit(projectPath: string, message: string): Observable<{success: boolean; sha: string}> {
    return this.http.post<{success: boolean; sha: string}>(`${this.baseUrl}/commit`, {
      path: projectPath,
      message
    });
  }

  push(projectPath: string, remote: string): Observable<{success: boolean}> {
    return this.http.post<{success: boolean}>(`${this.baseUrl}/push`, {
      path: projectPath,
      remote
    });
  }

  status(projectPath: string): Observable<GitStatus> {
    return this.http.get<GitStatus>(`${this.baseUrl}/status`, {
      params: { path: projectPath }
    });
  }
}

interface GitStatus {
  initialized: boolean;
  branch: string;
  hasChanges: boolean;
  files: { path: string; status: string }[];
}
```

### Step 2: Create Backend Git Endpoints

**File**: `server.js`

**Purpose**: Execute git commands

**Pattern**:
```javascript
app.post('/api/git/init', async (req, res) => {
  const { path } = req.body;
  try {
    await execPromise('git init', { cwd: path });
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/git/commit', async (req, res) => {
  const { path, message } = req.body;
  try {
    await execPromise('git add -A', { cwd: path });
    const result = await execPromise(`git commit -m "${message}"`, { cwd: path });
    const sha = await execPromise('git rev-parse HEAD', { cwd: path });
    res.json({ success: true, sha: sha.trim() });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/git/push', async (req, res) => {
  const { path, remote } = req.body;
  try {
    await execPromise(`git push ${remote}`, { cwd: path });
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/api/git/status', async (req, res) => {
  const { path } = req.query;
  try {
    const status = await execPromise('git status --porcelain', { cwd: path });
    const branch = await execPromise('git branch --show-current', { cwd: path });
    res.json({
      initialized: true,
      branch: branch.trim(),
      hasChanges: status.trim().length > 0,
      files: parseGitStatus(status)
    });
  } catch (error) {
    res.json({ initialized: false, branch: '', hasChanges: false, files: [] });
  }
});
```

### Step 3: Create Export Dialog

**File**: `src/app/components/export-dialog/export-dialog.component.ts`

**Purpose**: UI for exporting project to disk

**Pattern**:
```typescript
@Component({
  selector: 'app-export-dialog',
  // Modal with:
  // - Target folder input
  // - Initialize git checkbox
  // - Remote URL input (optional)
  // - Export button
})
export class ExportDialogComponent {
  @Input() project: Project;

  targetPath = '';
  initGit = true;
  remoteUrl = '';

  async export() {
    // Write files to target path
    for (const spec of this.project.specs) {
      await this.writeFile(this.targetPath, spec.filename, spec.content);
    }

    // Initialize git if requested
    if (this.initGit) {
      await this.gitService.init(this.targetPath).toPromise();
      await this.gitService.commit(this.targetPath, 'Initial spec commit').toPromise();
    }

    // Push to remote if provided
    if (this.remoteUrl) {
      await this.execRemote(this.targetPath, this.remoteUrl);
      await this.gitService.push(this.targetPath, 'origin').toPromise();
    }
  }
}
```

### Step 4: Add Git Status to Sidebar

**File**: `src/app/components/sidebar/sidebar.component.ts`

**Purpose**: Show git status indicators

**Pattern**:
```typescript
// In template
<div class="project-header">
  <span>{{ project.name }}</span>
  @if (project.gitStatus?.hasChanges) {
    <span class="git-indicator modified">●</span>
  }
</div>

// In component
async loadGitStatus(project: Project) {
  if (project.path) {
    project.gitStatus = await this.gitService.status(project.path).toPromise();
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
npm start

# Create or open a project
# Click "Export" in sidebar
# Select a target folder
# Check "Initialize git"
# Click Export
```

**Expected Result**:
- [ ] Files exported to target folder
- [ ] Git repo initialized if selected
- [ ] Initial commit created
- [ ] `git log` shows commit
- [ ] Remote push works if URL provided

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark done
2. All MVP tasks complete — proceed to refinement

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking
