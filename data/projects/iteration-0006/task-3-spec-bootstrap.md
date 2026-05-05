# 🛠️ Task 3: Spec Bootstrap

**Purpose**: Take a brain dump and generate structured spec documents — go from unstructured idea to capability folder in minutes.

**Effort**: 2 days

**Dependencies**: Task 2 (AI Text Operations)

**Parallel With**: —

**Blocks**: Task 4 (Agent Integration)

**Related**:
- [🏗️ Architecture](./architecture.md)
- [🎯 Epic](./epic.md)

---

## Overview

### What's Included
- Bootstrap modal UI for brain dump input
- Generate analysis.md (problems)
- Generate epic.md (scope, tasks)
- Generate architecture.md (design)
- Generate implementation guides (one per task)
- Generate spec-index.md, timeline.md, README.md
- Progress indicator during generation

### What's NOT Included
- Multiple capability folders per project — MVP is single capability
- Custom templates — built-in prompts only
- Edit during generation — wait for completion

---

## Prerequisites

Before starting:
- Task 2 complete (AI operations working)
- Understanding of documentation guidelines (Analysis → Epic → Architecture → Implementation)

---

## Implementation Steps

### Step 1: Create Bootstrap Modal

**File**: `src/app/components/new-project/new-project.component.ts`

**Purpose**: UI for entering brain dump and triggering generation

**Pattern**:
```typescript
@Component({
  selector: 'app-new-project',
  // Modal overlay
  // Input for capability name
  // Textarea for brain dump
  // "Generate" button
  // Progress steps display
})
export class NewProjectComponent {
  projectName = '';
  brainDump = '';
  generating = false;
  steps = [
    { label: 'Analyzing problems...', done: false },
    { label: 'Defining scope & tasks...', done: false },
    { label: 'Designing architecture...', done: false },
    { label: 'Creating implementation guides...', done: false },
  ];
}
```

### Step 2: Create Document Generation Prompts

**File**: `src/app/components/new-project/new-project.component.ts`

**Purpose**: Prompts that produce constellation-quality docs

**Pattern**:
```typescript
buildAnalysisPrompt(): string {
  return `You are generating an **Analysis** document.
  // Template with required sections
  // Cross-references to Epic, Architecture
  INPUT: ${this.brainDump}`;
}
// Similar for buildEpicPrompt, buildArchitecturePrompt, buildImplementationGuidePrompt
```

### Step 3: Implement Sequential Generation

**Purpose**: Generate docs in order, passing context forward

**Pattern**:
```typescript
async bootstrap() {
  this.generating = true;
  // Phase 1: Analysis
  const analysis = await this.generateDoc('analysis.md', this.buildAnalysisPrompt());
  // Phase 2: Epic (can reference analysis)
  const epic = await this.generateDoc('epic.md', this.buildEpicPrompt());
  // Phase 3: Architecture
  const arch = await this.generateDoc('architecture.md', this.buildArchitecturePrompt());
  // Phase 4: Implementation guides (one per task)
  const tasks = this.extractTasksFromEpic(epic);
  for (const task of tasks) {
    await this.generateDoc(`task-${task.num}-*.md`, this.buildImplementationGuidePrompt(task));
  }
}
```

### Step 4: Wire to Sidebar

**File**: `src/app/app.component.ts`

**Purpose**: Show generated project in sidebar

**Pattern**:
```typescript
onProjectCreated(project: BootstrappedProject) {
  this.projects.push({
    id: `project-${Date.now()}`,
    name: project.name,
    specs: project.files.map(f => ({ filename: f.filename, content: f.content }))
  });
}
```

---

## Verification

```bash
npm start
# Click "+ New Capability"
# Enter name: "Test Product"
# Enter brain dump: "People need X. Problem is Y. Could build Z."
# Click Generate
```

**Expected Result**:
- [ ] Progress shows each step
- [ ] 6+ files generated (analysis, epic, architecture, timeline, spec-index, README)
- [ ] Implementation guides generated for each task
- [ ] Files appear in sidebar
- [ ] Content has correct cross-references

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark done
2. Proceed to Task 4: Agent Integration

---

## Related Documents

- [🏗️ Architecture](./architecture.md) – Design rationale
- [🎯 Epic](./epic.md) – Task scope
- [📅 Timeline](./timeline.md) – Status tracking
