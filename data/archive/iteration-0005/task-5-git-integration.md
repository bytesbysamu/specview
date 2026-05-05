# 🛠️ Task 5: Git Integration

**Purpose**: Version specs alongside code — MD files as source code.

**Effort**: 1 day

**Dependencies**: Task 1 (Document-First Editor)

**Parallel With**: Task 2 (AI Text Operations)

**Blocks**: —

**Related**:
- [🏗️ Architecture](./architecture.md)
- [🎯 Epic](./epic.md)

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

  init(projectPath: string): Observable<{success: boolean}> { ... }
  commit(projectPath: string, message: string): Observable<{success: boolean; sha: string}> { ... }
  push(projectPath: string, remote: string): Observable<{success: boolean}> { ... }
  status(projectPath: string): Observable<GitStatus> { ... }
}
```

### Step 2: Create Backend Git Endpoints

**File**: `server.js`

**Purpose**: Execute git commands

**Pattern**:
```javascript
app.post('/api/git/init', async (req, res) => {
  const { path } = req.body;
  await execPromise('git init', { cwd: path });
  res.json({ success: true });
});

app.post('/api/git/commit', async (req, res) => {
  const { path, message } = req.body;
  await execPromise('git add -A', { cwd: path });
  await execPromise(`git commit -m "${message}"`, { cwd: path });
  res.json({ success: true });
});
```

### Step 3: Create Export Dialog

**File**: `src/app/components/export-dialog/export-dialog.component.ts`

**Purpose**: UI for exporting project to disk

**Pattern**:
```typescript
@Component({
  selector: 'app-export-dialog',
})
export class ExportDialogComponent {
  @Input() project: Project;
  targetPath = '';
  initGit = true;
  remoteUrl = '';

  async export() {
    // Write files, init git, push if remote provided
  }
}
```

### Step 4: Add Git Status to Sidebar

**File**: `src/app/components/sidebar/sidebar.component.ts`

**Purpose**: Show git status indicators

**Pattern**:
```typescript
// Show modified indicator
@if (project.gitStatus?.hasChanges) {
  <span class="git-indicator modified">●</span>
}
```

---

## Verification

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

- [🏗️ Architecture](./architecture.md) – Design rationale
- [🎯 Epic](./epic.md) – Task scope
- [📅 Timeline](./timeline.md) – Status tracking
