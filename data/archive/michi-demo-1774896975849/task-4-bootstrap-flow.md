# 🛠️ Task 4: Bootstrap Flow

**Purpose**: Build a modal that accepts unstructured brain dump text and generates a complete spec structure (analysis.md, epic.md, architecture.md) via AI, demonstrating Spec Doc's core value proposition.

**Effort**: 2 days

**Dependencies**: Task 1 (Monaco Editor), Task 2 (Preview Pane), Task 3 (AI Operations) must be complete

**Parallel With**: —

**Blocks**: Full product demonstration, user onboarding flow

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- New project modal with brain dump textarea
- Multi-file generation pipeline (brain dump → 3+ spec files)
- Project creation in sidebar with generated files
- Loading state during generation
- Basic error handling

### What's NOT Included
- Template selection — single default structure for MVP
- Streaming preview of generation — batch response only
- Edit/regenerate individual sections — use text operations post-generation
- Project persistence to disk — in-memory for demo

---

## Prerequisites

Before starting:
- AI service configured and working (Task 3)
- Projects service exists with file tree structure
- Sidebar component can display project files
- Understanding of Angular reactive forms and dialogs

---

## Implementation Steps

### Step 1: Create New Project Modal Component

**File**: `src/app/components/new-project/new-project.component.ts`

**Purpose**: Modal UI that captures project name and brain dump text

The modal needs two inputs: a project name (for sidebar display) and a freeform textarea for the brain dump. Use Angular's dialog pattern with form validation.

**Pattern**:
```typescript
@Component({
  selector: 'app-new-project',
  template: `
    <div class="modal-overlay" (click)="close()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <h2>Bootstrap New Project</h2>
        
        <form [formGroup]="form" (ngSubmit)="onSubmit()">
          <label>
            Project Name
            <input formControlName="name" placeholder="my-saas-product" />
          </label>
          
          <label>
            Brain Dump
            <textarea 
              formControlName="brainDump" 
              rows="12"
              placeholder="Describe your product idea, problems it solves, target users, features you're imagining..."
            ></textarea>
          </label>
          
          <div class="actions">
            <button type="button" (click)="close()">Cancel</button>
            <button type="submit" [disabled]="!form.valid || isGenerating">
              {{ isGenerating ? 'Generating...' : 'Generate Specs' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  `
})
export class NewProjectComponent {
  form = new FormGroup({
    name: new FormControl('', [Validators.required, Validators.pattern(/^[a-z0-9-]+$/)]),
    brainDump: new FormControl('', [Validators.required, Validators.minLength(50)])
  });
  
  isGenerating = false;
}
```

### Step 2: Create Bootstrap Service

**File**: `src/app/services/bootstrap.service.ts`

**Purpose**: Orchestrate the multi-file generation pipeline

This service takes raw brain dump text and coordinates generating multiple spec files. Each file type has a specific prompt that shapes the AI output. Generate sequentially to allow context building (analysis informs epic, epic informs architecture).

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class BootstrapService {
  constructor(private ai: AiService) {}

  async bootstrap(brainDump: string): Promise<GeneratedProject> {
    // Step 1: Generate analysis (problem space)
    const analysis = await this.generateFile('analysis', brainDump, {
      systemPrompt: ANALYSIS_PROMPT,
      context: null
    });

    // Step 2: Generate epic (scope) - uses analysis as context
    const epic = await this.generateFile('epic', brainDump, {
      systemPrompt: EPIC_PROMPT,
      context: { analysis }
    });

    // Step 3: Generate architecture - uses both as context
    const architecture = await this.generateFile('architecture', brainDump, {
      systemPrompt: ARCHITECTURE_PROMPT,
      context: { analysis, epic }
    });

    return {
      files: [
        { name: 'analysis.md', content: analysis },
        { name: 'epic.md', content: epic },
        { name: 'architecture.md', content: architecture }
      ]
    };
  }

  private async generateFile(
    type: string, 
    brainDump: string, 
    options: GenerateOptions
  ): Promise<string> {
    const prompt = this.buildPrompt(type, brainDump, options.context);
    return this.ai.generate(prompt, options.systemPrompt);
  }
}
```

### Step 3: Define Generation Prompts

**File**: `src/app/services/bootstrap.prompts.ts`

**Purpose**: System prompts that shape each document type

Each prompt encodes the document's "one job" as defined in the architecture. These are the core IP—treat them as production code.

**Pattern**:
```typescript
export const ANALYSIS_PROMPT = `
You are generating an Analysis document for a new product.

## Your ONE Job
Identify and articulate the core problem space. Focus on:
- Who has this problem (target users)
- What the problem actually is (not symptoms)
- Why existing solutions fail
- What success looks like

## Output Format
Markdown starting with #. No preamble. Include:
- Problem Statement (2-3 sentences, crisp)
- Target Users (specific, not generic)
- Current Alternatives (and why they fail)
- Success Criteria (measurable outcomes)
`;

export const EPIC_PROMPT = `
You are generating an Epic document that defines scope.

## Your ONE Job  
Define what we're building and what we're NOT building. Include:
- Clear scope boundaries
- Task breakdown with dependencies
- Success criteria per task

## Context
You have access to the Analysis document. Reference it, don't duplicate.

## Output Format
Markdown starting with #. Include task list with effort estimates.
`;

export const ARCHITECTURE_PROMPT = `
You are generating an Architecture document.

## Your ONE Job
Design decisions that will outlive the code. Include:
- Core abstractions and why
- Data flow
- Integration points
- What's intentionally deferred

## Context
You have Analysis (problem) and Epic (scope). Reference both.

## Output Format
Markdown starting with #. Diagrams as ASCII or mermaid.
`;
```

### Step 4: Wire Modal to Projects Service

**File**: `src/app/components/new-project/new-project.component.ts` (update)

**Purpose**: Connect generation output to project creation

When generation completes, create a new project entry with the generated files and navigate to it.

**Pattern**:
```typescript
async onSubmit() {
  if (!this.form.valid) return;
  
  this.isGenerating = true;
  
  try {
    const { name, brainDump } = this.form.value;
    
    // Generate all spec files
    const generated = await this.bootstrap.bootstrap(brainDump);
    
    // Create project with generated files
    const project = await this.projects.create({
      name,
      files: generated.files
    });
    
    // Navigate to first file (analysis.md)
    this.projects.openFile(project.id, 'analysis.md');
    
    this.close();
  } catch (error) {
    this.error = 'Generation failed. Please try again.';
  } finally {
    this.isGenerating = false;
  }
}
```

### Step 5: Add Trigger to Sidebar

**File**: `src/app/components/sidebar/sidebar.component.ts`

**Purpose**: Button that opens the bootstrap modal

Add a "New Project" button at the top of the sidebar that opens the modal.

**Pattern**:
```typescript
@Component({
  template: `
    <div class="sidebar">
      <button class="new-project-btn" (click)="openNewProject()">
        + New Project
      </button>
      
      <div class="project-list">
        <!-- existing project tree -->
      </div>
    </div>
  `
})
export class SidebarComponent {
  showModal = false;
  
  openNewProject() {
    this.showModal = true;
  }
}
```

### Step 6: Add Loading State UI

**File**: `src/app/components/new-project/new-project.component.ts` (update)

**Purpose**: Show progress during multi-file generation

Since generation takes 30-60 seconds for three files, provide visual feedback on progress.

**Pattern**:
```typescript
// Add to component
generationPhase: 'idle' | 'analysis' | 'epic' | 'architecture' | 'done' = 'idle';

// Update template
<div *ngIf="isGenerating" class="progress">
  <div class="phase" [class.active]="generationPhase === 'analysis'">
    Analyzing problem space...
  </div>
  <div class="phase" [class.active]="generationPhase === 'epic'">
    Defining scope...
  </div>
  <div class="phase" [class.active]="generationPhase === 'architecture'">
    Designing architecture...
  </div>
</div>
```

### Step 7: Handle Generation Errors

**File**: `src/app/services/bootstrap.service.ts` (update)

**Purpose**: Graceful failure with partial results

If generation fails mid-way, return what was generated rather than losing everything.

**Pattern**:
```typescript
async bootstrap(brainDump: string): Promise<GeneratedProject> {
  const files: GeneratedFile[] = [];
  
  try {
    const analysis = await this.generateFile('analysis', brainDump, {});
    files.push({ name: 'analysis.md', content: analysis });
    
    const epic = await this.generateFile('epic', brainDump, { context: { analysis } });
    files.push({ name: 'epic.md', content: epic });
    
    const architecture = await this.generateFile('architecture', brainDump, { 
      context: { analysis, epic } 
    });
    files.push({ name: 'architecture.md', content: architecture });
    
  } catch (error) {
    if (files.length === 0) throw error; // Nothing generated, rethrow
    // Partial success - return what we have
    console.warn('Bootstrap partial failure:', error);
  }
  
  return { files, partial: files.length < 3 };
}
```

---

## Verification

How to verify this implementation works:

```bash
# Start the dev server
npm run dev

# Open browser to http://localhost:4201
```

**Manual Test**:
1. Click "+ New Project" in sidebar
2. Enter project name: `test-product`
3. Paste brain dump text (minimum 50 characters):
   ```
   I want to build a tool that helps developers write better documentation. 
   The problem is docs are always outdated because they're separate from code.
   Target users are small dev teams. Should integrate with GitHub.
   ```
4. Click "Generate Specs"
5. Wait for generation (observe phase indicators)

**Expected Result**: 
- New project appears in sidebar with name `test-product`
- Project contains three files: `analysis.md`, `epic.md`, `architecture.md`
- Each file opens in editor with generated content
- Content is coherent and references other documents appropriately

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 4 done
2. Test with various brain dump inputs to validate prompt quality
3. Iterate on prompts based on output quality (prompts are code)

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for document-as-interface
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking