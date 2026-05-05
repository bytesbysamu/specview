Now I have enough context. Generating the implementation guide.

# 🛠️ Task 11: Generate Next Task Button

**Purpose**: Add a per-project "+ Generate Next Task" sidebar action that generates the implementation guide for the next un-generated task in an epic, sharing one prompt builder between bootstrap and this new path.

**Effort**: 1 day

**Dependencies**: Task 3 (Spec Bootstrap — already shipped; `buildImplementationGuidePrompt` lives in `NewProjectComponent`)

**Parallel With**: —

**Blocks**: Any future "regenerate task", "split task", or "add task N+1" UX that needs a single source of truth for the impl-guide prompt.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Today, the only path that produces implementation guides is `NewProjectComponent.bootstrap()`, which holds both `buildImplementationGuidePrompt()` and `extractTasksFromEpic()` as private methods (~180 lines of the 1315-line component at `src/app/components/new-project/new-project.component.ts`). This means incremental task addition is impossible — the user must re-bootstrap, overwriting hand-edited `analysis.md`/`epic.md`/`architecture.md`. This task extracts both methods into a new `ImplementationGuideService`, then adds a per-project sidebar action `generate-next-task` that uses the service to produce `task-N-{slug}.md` alongside existing task files. It fits the epic's agent-integration track: specs are the source of truth, and users need to evolve a project's task list without destroying context. The refactor is load-bearing — the service is the single source of truth for the impl-guide prompt across every future entry point.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                           # flag any unrelated M/?? entries
git diff HEAD -- src/app/components/new-project/new-project.component.ts \
                 src/app/components/sidebar/sidebar.component.ts \
                 src/app/app.component.ts \
                 server.test.js                                      # confirm target files are clean
npm run test:server                                                  # baseline: record pass count
```

**If working tree is dirty on target files**: stash them or commit the unrelated changes on a separate branch BEFORE starting. The existing `git status` shows `M src/app/components/operation-bar/operation-bar.component.ts`, `M src/app/services/ai.service.ts`, `M src/app/services/timeline-parser.service.ts`, `M server.js` — these are pre-existing and outside this task's scope; leave them untouched.

**Baseline to record**: `npm run test:server` pass count (observed format: `# pass N` in node:test output). Write that number down — Section 7 requires it.

---

## 3. Files

### To Create (new)
- `src/app/services/implementation-guide.service.ts` — new service holding `buildImplementationGuidePrompt()` + `extractTasksFromEpic()`. Injects `BuilderService`, `PrinciplesService`, `CodebaseService` the same way `NewProjectComponent` does today (see constructor at lines 395–414 of `new-project.component.ts`). Exposes a `generateNextTask(projectId, projectName)` method that reads the project via `ProjectsService.get()`, finds the first task whose `task-N-*.md` file is missing, calls `AiService.generate()` with the built prompt, writes via `ProjectsService.updateFile()`, and returns `{ filename, content, taskNum, taskName } | null` (null = "no ungenerated tasks").

### To Modify (cite CODEBASE CONTEXT)
- `src/app/components/new-project/new-project.component.ts` — remove the private `buildImplementationGuidePrompt()` (lines 1123–1305) and `extractTasksFromEpic()` (lines 564–581); inject `ImplementationGuideService` in the constructor (line 395–401); delegate both call sites (line 507 `extractTasksFromEpic`, line 542 `buildImplementationGuidePrompt`) to the service. `getBuilderBlock`/`getPrinciplesBlock`/`getCodebaseBlock` helpers that were only used by the removed method can also be deleted if no other method references them — verify with a grep before deleting.
- `src/app/components/sidebar/sidebar.component.ts` — extend `SidebarAction` type (line 20) to include `'generate-next-task'`; add a per-project button in the `.project-header` block (lines 42–56) that is only rendered when `project.isPersisted` (mirroring the delete-btn pattern at lines 50–56); emit via existing `action` output but carry the project via a new output `generateNextTask = new EventEmitter<Project>()` so the app knows which project to target.
- `src/app/app.component.ts` — add a handler `onGenerateNextTask(project: Project)`, wired via new `(generateNextTask)="onGenerateNextTask($event)"` on `<app-sidebar>` (line 27–34); the handler calls `ImplementationGuideService.generateNextTask(project.id, project.name)`, drives the `outputPanel` state already present (lines 273–281), shows a toast when null is returned, and on success: pushes the new file into `project.specs`, sets `this.currentFile = result.filename`, loads its content. Inject `ImplementationGuideService` in the constructor (lines 286–292).
- `server.test.js` — append a new `describe('Generate Next Task Button — Task 11')` block at the end (after the existing `Impl Guide Prompt — Executor Protocol` block that ends at line 655). All assertions are source-file reads, same pattern as every existing test.

### To Leave Alone
- `server.js` — no backend changes needed. `ProjectsService.updateFile()` already writes any filename via `PUT /api/projects/:id/files/:filename`.
- `src/app/services/ai.service.ts`, `src/app/services/projects.service.ts`, `src/app/services/builder.service.ts`, `src/app/services/principles.service.ts`, `src/app/services/codebase.service.ts` — consumed, not modified.
- `src/app/components/output-panel/output-panel.component.ts` — reused as-is; its `running`/`success`/`files` inputs already match this use case.
- `eval/` and `specs/` directories — unrelated.
- `projects/` directory — runtime data, never edit from code.
- The pre-existing modified files listed in `git status` (see Section 2) — outside this task's scope.

---

## 4. Implementation Steps

### Step 1: Create `ImplementationGuideService` and move prompt + parser into it

**Action**: Create the new Angular service. Copy `buildImplementationGuidePrompt()` verbatim from `new-project.component.ts` (lines 1123–1305) and `extractTasksFromEpic()` verbatim (lines 564–581). Add the three context-block helpers `getBuilderBlock`/`getPrinciplesBlock`/`getCodebaseBlock` (lines 781–797). Add `generateNextTask()` as the public entry point. Use constructor injection via class `private`-prefix params (that's the existing codebase style — `new-project.component.ts` line 395).

**File**: `src/app/services/implementation-guide.service.ts` (new)

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AiService } from './ai.service';
import { BuilderService } from './builder.service';
import { PrinciplesService } from './principles.service';
import { CodebaseService } from './codebase.service';
import { ProjectsService } from './projects.service';

export interface EpicTask { num: string; name: string; effort: string; }
export interface GeneratedTaskFile {
  filename: string; content: string; taskNum: string; taskName: string;
}

@Injectable({ providedIn: 'root' })
export class ImplementationGuideService {
  private builderContext = '';
  private principlesContext = '';
  private codebaseContext = '';

  constructor(
    private ai: AiService,
    private builder: BuilderService,
    private principles: PrinciplesService,
    private codebase: CodebaseService,
    private projects: ProjectsService
  ) {
    this.builder.get().subscribe({ next: p => (this.builderContext = p.content), error: () => {} });
    this.principles.get().subscribe({ next: p => (this.principlesContext = p.content), error: () => {} });
    this.codebase.get().subscribe({ next: c => (this.codebaseContext = c.content), error: () => {} });
  }

  extractTasksFromEpic(epicContent: string): EpicTask[] {
    // MOVED VERBATIM from new-project.component.ts lines 564-581
    // Keep regex identical — server.test.js "Task Parser" block asserts shape.
  }

  buildImplementationGuidePrompt(task: EpicTask, epicContent: string, archContent: string): string {
    // MOVED VERBATIM from new-project.component.ts lines 1123-1305
    // The 9-section template + hard rules. Callers in server.test.js
    // "Impl Guide Prompt — Executor Protocol" block read via this path.
  }

  async generateNextTask(projectId: string, projectName: string): Promise<GeneratedTaskFile | null> {
    const project = await firstValueFrom(this.projects.get(projectId));
    const epic = project.specs.find(s => s.filename === 'epic.md')?.content ?? '';
    const arch = project.specs.find(s => s.filename === 'architecture.md')?.content ?? '';
    const tasks = this.extractTasksFromEpic(epic);
    const existingTaskNums = new Set(
      project.specs
        .map(s => s.filename.match(/^task-(\d+)-/))       // matches task-3- AND task-3-- (double-dash)
        .filter((m): m is RegExpMatchArray => m !== null)
        .map(m => m[1])
    );
    const next = tasks.find(t => !existingTaskNums.has(t.num));
    if (!next) return null;
    const prompt = this.buildImplementationGuidePrompt(next, epic, arch);
    const resp = await firstValueFrom(this.ai.generate(prompt));
    const slug = next.name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    const filename = `task-${next.num}-${slug}.md`;
    const content = resp?.text ?? '';
    await firstValueFrom(this.projects.updateFile(projectId, filename, content));
    return { filename, content, taskNum: next.num, taskName: next.name };
  }

  private getBuilderBlock(): string { /* verbatim from new-project.component.ts 781-785 */ }
  private getPrinciplesBlock(): string { /* verbatim 787-791 */ }
  private getCodebaseBlock(): string { /* verbatim 793-797 */ }
}
```

**Verify**: `npx tsc --noEmit -p .` — expect no new TypeScript errors. Then `npm run test:server` — the "Impl Guide Prompt — Executor Protocol" block currently reads `new-project.component.ts`; it will still pass until Step 2 removes the methods from that file. Do not commit yet.

### Step 2: Delegate from `NewProjectComponent` to the new service

**Action**: In `src/app/components/new-project/new-project.component.ts`, inject `ImplementationGuideService`; replace the call at line 507 (`this.extractTasksFromEpic(epicContent)` → `this.implGuide.extractTasksFromEpic(epicContent)`) and the call at line 542 (`this.buildImplementationGuidePrompt(task, epicContent, archContent)` → `this.implGuide.buildImplementationGuidePrompt(task, epicContent, archContent)`). Then delete the private methods `extractTasksFromEpic` (lines 564–581) and `buildImplementationGuidePrompt` (lines 1123–1305). Grep the file for `getBuilderBlock`, `getPrinciplesBlock`, `getCodebaseBlock` — these helpers are only used by the now-deleted method, so delete them too (and the `builderContext`/`principlesContext`/`codebaseContext` fields at lines 390–392 and their subscriptions in the constructor at lines 402–413 — the bootstrap chain uses the other three prompt builders which all use these helpers; re-verify before deleting).

**File**: `src/app/components/new-project/new-project.component.ts`

**Pattern**:
```typescript
// Constructor signature — add implGuide
constructor(
  private aiService: AiService,
  private builderService: BuilderService,
  private principlesService: PrinciplesService,
  private codebaseService: CodebaseService,
  private projectsService: ProjectsService,
  private implGuide: ImplementationGuideService
) { /* keep the existing context subscriptions — buildAnalysisPrompt/buildEpicPrompt/buildArchitecturePrompt still need them */ }

// Phase 2 call site (was line 507)
const tasks = this.implGuide.extractTasksFromEpic(epicContent);

// Phase 3 call site (was line 542)
const prompt = this.implGuide.buildImplementationGuidePrompt(task, epicContent, archContent);

// DELETE private extractTasksFromEpic (old 564-581) and buildImplementationGuidePrompt (old 1123-1305)
```

Re-verify before deleting `getBuilderBlock`/`getPrinciplesBlock`/`getCodebaseBlock` with a grep: the other prompt builders `buildAnalysisPrompt` (line 811), `buildEpicPrompt` (line 854), `buildArchitecturePrompt` (line 969) all call `this.getBuilderBlock()` — so KEEP the helpers and KEEP the context fields + subscriptions in `NewProjectComponent`. Only the impl-guide usage moves to the service. This is important: do not over-delete.

**Verify**: `npm run test:server` — the "Impl Guide Prompt — Executor Protocol" block (lines 544–655 of `server.test.js`) reads `new-project.component.ts` looking for `buildImplementationGuidePrompt`. After Step 2 these assertions will FAIL. That's expected and fixed in Step 5 (point the tests at `implementation-guide.service.ts`). Don't worry about it yet; just confirm the TypeScript compiles: `npx tsc --noEmit -p .`.

### Step 3: Add sidebar action per-project

**Action**: In `src/app/components/sidebar/sidebar.component.ts`, extend the `SidebarAction` type (line 20) and add a new output `generateNextTask`. In the template at the `.project-header` block (lines 42–56), add a generate-next-task button next to the existing delete-btn, gated by `*ngIf="project.isPersisted"`. Do NOT reuse the existing `action` output — this action carries a `Project` payload, not a bare string.

**File**: `src/app/components/sidebar/sidebar.component.ts`

**Pattern**:
```typescript
export type SidebarAction = 'implement' | 'copy' | 'new-project' | 'delete-project'
  | 'builder-profile' | 'principles' | 'codebase' | 'generate-next-task';

// In @Component template, inside the .project-header block after the delete button:
// <button *ngIf="project.isPersisted"
//   class="gen-next-btn"
//   (click)="onGenerateNextTask(project); $event.stopPropagation()"
//   title="Generate next implementation guide">+ task</button>

// Class body: new output and handler
@Output() generateNextTask = new EventEmitter<Project>();

onGenerateNextTask(project: Project): void {
  this.generateNextTask.emit(project);
}
```

Add a small style block for `.gen-next-btn` that follows the existing `.delete-btn` pattern (opacity 0 until hover, see lines 211–229 in the existing file).

**Verify**: `npx tsc --noEmit -p .` — expect no new errors. `ng build --configuration development` (or `npm run build`) — expect success.

### Step 4: Wire the handler in `AppComponent`

**Action**: In `src/app/app.component.ts`, bind the new sidebar output and implement the handler. Inject `ImplementationGuideService` in the constructor (lines 286–292). Reuse the existing `outputPanel` state shape (lines 273–281) to render progress — set `visible=true`, `running=true`, `taskName=<task name or 'Generate Next Task'>`. On success: append the generated file to `project.specs` (mirror the pattern used in `onProjectCreated` at lines 490–543), set `activeProjectId`, `currentFile`, and `content` to the new file, then set `outputPanel.success=true` and `outputPanel.running=false`. On null: show toast `"All tasks already generated"`. On error: `outputPanel.success=false`, append error text to `outputPanel.output`.

**File**: `src/app/app.component.ts`

**Pattern**:
```typescript
// Template: bind the new output on <app-sidebar> around line 27-34
// (generateNextTask)="onGenerateNextTask($event)"

// Constructor — add implGuide
constructor(
  private aiService: AiService,
  private http: HttpClient,
  private projectsService: ProjectsService,
  private implementationService: ImplementationService,
  private timelineParser: TimelineParserService,
  private implGuide: ImplementationGuideService
) { /* existing debounced save setup unchanged */ }

// New handler
async onGenerateNextTask(project: Project): Promise<void> {
  this.outputPanel = {
    visible: true, output: `Generating next task for ${project.name}…\n`,
    running: true, success: false, files: [],
    taskName: 'Generate Next Task', lastRequest: null
  };
  try {
    const result = await this.implGuide.generateNextTask(project.id, project.name);
    if (!result) {
      this.outputPanel.visible = false;
      this.showToast('All tasks already generated for this project');
      return;
    }
    // Append to sidebar
    const labelFromFilename = (f: string) =>
      f.replace('.md','').replace(/-/g,' ').replace(/\b\w/g, c => c.toUpperCase());
    project.specs = [...project.specs, {
      id: `gen-${project.specs.length}`,
      label: labelFromFilename(result.filename),
      filename: result.filename,
      content: result.content
    }];
    this.activeProjectId = project.id;
    this.currentFile = result.filename;
    this.content = result.content;
    this.outputPanel.output += `\nWrote ${result.filename} (${result.content.length} chars)\n`;
    this.outputPanel.running = false;
    this.outputPanel.success = true;
    this.outputPanel.files = [result.filename];
  } catch (err: any) {
    this.outputPanel.running = false;
    this.outputPanel.success = false;
    this.outputPanel.output += `\nFailed: ${err?.message ?? err}\n`;
  }
}
```

**Verify**: `npx tsc --noEmit -p .` — expect no new errors. Then manually: `npm run dev`, open `http://localhost:4201`, select a persisted project in the sidebar (e.g. `iteration-0006` has 5 tasks all generated — should toast "All tasks already generated"). Open a project with fewer tasks generated than epic rows; click `+ task`; confirm the output panel opens, a new `task-N-*.md` appears in the sidebar, and the editor jumps to it.

### Step 5: Add `server.test.js` assertions

**Action**: Append a new describe block at the end of `server.test.js` (after line 655). Update the existing `Impl Guide Prompt — Executor Protocol` block (lines 544–655) to read from `src/app/services/implementation-guide.service.ts` instead of `new-project.component.ts` — specifically, change the `SERVICE_PATH` constant at the top to a new `IMPL_GUIDE_SERVICE_PATH`, and update the `before()` hook at line 547–552 to read that file. Also update line 324–325 in the `Builder Context in All Operations` describe block which reads `buildImplementationGuidePrompt` from `NEW_PROJECT_PATH` — that must now read it from the service.

**File**: `server.test.js`

**Pattern**:
```javascript
// At top (after existing path constants around line 26-30):
const IMPL_GUIDE_SERVICE_PATH = path.join(__dirname, 'src/app/services/implementation-guide.service.ts');
const APP_PATH_REL = 'src/app/app.component.ts';  // existing reference, unchanged

// Modify existing "Impl Guide Prompt — Executor Protocol" before() hook:
before(() => {
  const code = readFile(IMPL_GUIDE_SERVICE_PATH);
  const start = code.indexOf('buildImplementationGuidePrompt');
  assert.ok(start > 0, 'buildImplementationGuidePrompt must exist in service');
  implPromptSection = code.substring(start, start + 8000);
});

// Modify existing "Builder Context in All Operations" — implPrompt assertion:
const svc = readFile(IMPL_GUIDE_SERVICE_PATH);
const implPrompt = svc.substring(
  svc.indexOf('buildImplementationGuidePrompt'),
  svc.indexOf('buildImplementationGuidePrompt') + 3000
);
assert.ok(implPrompt.includes('getBuilderBlock'),
  'implementation prompt should call getBuilderBlock');

// New describe block at end of file:
describe('Generate Next Task Button — Task 11', () => {
  it('ImplementationGuideService file exists', () => {
    assert.ok(fs.existsSync(IMPL_GUIDE_SERVICE_PATH),
      'implementation-guide.service.ts must exist');
  });

  it('service exposes extractTasksFromEpic', () => {
    const code = readFile(IMPL_GUIDE_SERVICE_PATH);
    assert.ok(/extractTasksFromEpic\s*\(/.test(code),
      'service should declare extractTasksFromEpic()');
  });

  it('service exposes buildImplementationGuidePrompt', () => {
    const code = readFile(IMPL_GUIDE_SERVICE_PATH);
    assert.ok(/buildImplementationGuidePrompt\s*\(/.test(code),
      'service should declare buildImplementationGuidePrompt()');
  });

  it('service exposes generateNextTask', () => {
    const code = readFile(IMPL_GUIDE_SERVICE_PATH);
    assert.ok(/generateNextTask\s*\(/.test(code),
      'service should expose generateNextTask() as public entry point');
  });

  it('detection regex handles double-dash task filenames', () => {
    const code = readFile(IMPL_GUIDE_SERVICE_PATH);
    const regexLine = code.match(/\/\^task-\\d\+\\?-\//) || code.match(/\/\^task-\(\\d\+\)-/);
    assert.ok(regexLine, 'service should match task-N- prefix (covers task-3--foo.md)');
    // Live check — load the regex pattern from the source and test it
    const re = /^task-(\d+)-/;
    assert.ok(re.test('task-3--photoshoot-route-camera-inference.md'),
      'regex must match double-dash filename');
    assert.ok(re.test('task-1-document-first-editor.md'),
      'regex must match single-dash filename');
    assert.equal(re.exec('task-3--foo.md')?.[1], '3',
      'regex must extract task number correctly for double-dash');
  });

  it('NewProjectComponent no longer declares buildImplementationGuidePrompt', () => {
    const code = readFile(NEW_PROJECT_PATH);
    assert.ok(!/private\s+buildImplementationGuidePrompt/.test(code),
      'NewProjectComponent must delegate to ImplementationGuideService, not declare the method');
  });

  it('NewProjectComponent no longer declares extractTasksFromEpic', () => {
    const code = readFile(NEW_PROJECT_PATH);
    assert.ok(!/private\s+extractTasksFromEpic/.test(code),
      'NewProjectComponent must delegate extractTasksFromEpic to the service');
  });

  it('NewProjectComponent injects ImplementationGuideService', () => {
    const code = readFile(NEW_PROJECT_PATH);
    assert.ok(code.includes('ImplementationGuideService'),
      'NewProjectComponent should inject ImplementationGuideService');
  });

  it('SidebarAction type includes generate-next-task', () => {
    const code = readFile(SIDEBAR_PATH);
    assert.ok(code.includes("'generate-next-task'"),
      'SidebarAction union must include generate-next-task');
  });

  it('Sidebar exposes generateNextTask output with Project payload', () => {
    const code = readFile(SIDEBAR_PATH);
    assert.ok(/generateNextTask\s*=\s*new\s+EventEmitter<Project>/.test(code),
      'Sidebar should declare generateNextTask EventEmitter<Project>');
  });

  it('Sidebar gates the button on project.isPersisted', () => {
    const code = readFile(SIDEBAR_PATH);
    const buttonMatch = code.match(/gen-next-btn[\s\S]{0,200}/);
    assert.ok(buttonMatch, 'sidebar template should contain gen-next-btn');
    assert.ok(buttonMatch[0].includes('isPersisted'),
      'gen-next-btn must only render when project.isPersisted');
  });

  it('AppComponent binds generateNextTask output', () => {
    const code = readFile(APP_PATH);
    assert.ok(code.includes('(generateNextTask)="onGenerateNextTask'),
      'AppComponent template should bind (generateNextTask) on <app-sidebar>');
  });

  it('AppComponent handler toasts when no ungenerated tasks remain', () => {
    const code = readFile(APP_PATH);
    const handlerStart = code.indexOf('onGenerateNextTask(');
    assert.ok(handlerStart > 0, 'onGenerateNextTask handler must exist');
    const handler = code.substring(handlerStart, handlerStart + 2000);
    assert.ok(/All tasks already generated/.test(handler),
      'handler must toast All tasks already generated when service returns null');
  });

  it('AppComponent handler uses the existing outputPanel state', () => {
    const code = readFile(APP_PATH);
    const handlerStart = code.indexOf('onGenerateNextTask(');
    const handler = code.substring(handlerStart, handlerStart + 2000);
    assert.ok(/this\.outputPanel\s*=/.test(handler) || handler.includes('this.outputPanel.'),
      'handler must drive this.outputPanel state (reusing the panel from the implement flow)');
  });
});
```

**Verify**: `npm run test:server` — expect all new assertions green AND the relocated "Impl Guide Prompt — Executor Protocol" assertions green. Record the new pass count.

---

## 5. Tests

Framework: `node:test` + `node:assert/strict` (matches `server.test.js` — see `describe`/`it`/`before` at lines 17–21). All assertions are source-file reads; there is no spin-up/HTTP piece for this task.

Concrete assertion bodies are embedded in Step 5 above. No stubs. Each `it()` has a `describe` parent, a real regex or string check, and a failure message that names the contract being violated.

Additionally, update two existing `before`/assertion sites in `server.test.js`:

```javascript
// Relocation 1 — "Impl Guide Prompt — Executor Protocol" before() hook at line 547
before(() => {
  const code = readFile(IMPL_GUIDE_SERVICE_PATH);   // was: readFile(NEW_PROJECT_PATH)
  const start = code.indexOf('buildImplementationGuidePrompt');
  assert.ok(start > 0, 'buildImplementationGuidePrompt must exist in service');
  implPromptSection = code.substring(start, start + 8000);
});

// Relocation 2 — "Builder Context in All Operations" line 324-325
const svc = readFile(IMPL_GUIDE_SERVICE_PATH);
const implPrompt = svc.substring(
  svc.indexOf('buildImplementationGuidePrompt'),
  svc.indexOf('buildImplementationGuidePrompt') + 3000
);
assert.ok(implPrompt.includes('getBuilderBlock'),
  'impl prompt should call getBuilderBlock');
```

---

## 6. Commit Plan

One commit per logical unit. Each commit is independently revertible.

1. `refactor(impl-guide): extract ImplementationGuideService from NewProjectComponent` — new file `src/app/services/implementation-guide.service.ts` + modified `src/app/components/new-project/new-project.component.ts` delegating to the service. No behavior change.
2. `feat(sidebar): add per-project generate-next-task action` — modified `src/app/components/sidebar/sidebar.component.ts`: type extension + button + EventEmitter.
3. `feat(app): wire generate-next-task handler` — modified `src/app/app.component.ts`: sidebar binding + `onGenerateNextTask` handler reusing the output panel.
4. `test(impl-guide): assert service, sidebar wiring, app handler, double-dash regex` — modified `server.test.js`: relocate two existing reads to the service path + new `Generate Next Task Button — Task 11` describe block.

**Deviation logging**: if a step deviates from this guide (e.g. the helper methods `getBuilderBlock`/`getPrinciplesBlock`/`getCodebaseBlock` turn out to be unused in `NewProjectComponent` after Step 2 and you delete them), prefix the relevant commit body with `Deviations:` and one line per deviation. Example: `Deviations: deleted getBuilderBlock from NewProjectComponent (only impl-guide used it after delegation; grep confirmed).`

---

## 7. Verification

```bash
npm run test:server       # node --test server.test.js — source-contract tests
npx tsc --noEmit -p .     # type check (frontend)
npm run build             # angular production build — catch template errors
```

**Expected delta**: `N → N + 13` passing (12 new `it()` in the Task 11 describe + 1 regex detection assertion counts as a single `it` block). Zero pre-existing tests broken. If the pre-existing count was e.g. 60, expect 73 after.

**Manual smoke test** (do this once before the final commit):
```bash
npm run dev
# → http://localhost:4201
# 1. Pick a persisted project whose epic has more task rows than on-disk task-N-*.md files
#    (projects/bubls2-1776263128609 is a candidate — verify epic row count vs task-*.md count first)
# 2. Click "+ task" on that project's header
# 3. Confirm: output panel opens, running spinner, eventual green check, new task-N-*.md in sidebar,
#    editor jumps to it, content is an executor-ready impl guide.
# 4. Click "+ task" on iteration-0006 (all 5 tasks already generated) → toast "All tasks already generated"
```

---

## 8. Rollback

- **Per-step**: every commit in Section 6 is independently revertible via `git revert <sha>`. Revert in reverse order if you need to unwind everything: tests → app wiring → sidebar → service refactor.
- **Per-branch**: if verification fails catastrophically (e.g. bootstrap broken, frontend won't build), `git reset --hard <pre-task-sha>` where `<pre-task-sha>` is the commit hash recorded from `git rev-parse HEAD` BEFORE Step 1. If a feature branch was used, you may delete it with `git branch -D <branch>` [REQUIRES APPROVAL] — confirm with the user before discarding work.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** — e.g. line numbers in `new-project.component.ts` shifted because of unrelated edits in the working tree. Re-anchor by method name (`buildImplementationGuidePrompt`, `extractTasksFromEpic`) rather than line number. Flag in the commit body as `Deviations: line anchor shifted — re-anchored on method name`.
- **Helper ownership surprise** — if any of `getBuilderBlock`/`getPrinciplesBlock`/`getCodebaseBlock` turns out to be used ONLY by the impl-guide path after Step 2 delegation, delete it from `NewProjectComponent`; but if the other builders (`buildAnalysisPrompt`/`buildEpicPrompt`/`buildArchitecturePrompt`) still call them, KEEP them. Grep before cutting.
- **Test framework mismatch** — all existing server tests use `node:test` + `assert/strict`. Stay with that. If you discover a new Karma/Jasmine test file has been added for the frontend since this guide was written, add component-level tests there as a bonus — but do not make the core contract depend on Karma because `npm run test:server` is the CI gate today.
- **Side-effect required** — any step that needs `git push`, `npm publish`, or deletion of files in `projects/` → STOP, mark `[REQUIRES APPROVAL]`, ask the user.
- **Step N unlocks an obvious simplification for Step N+1** — take it and log in the commit body. Example: if the service's `generateNextTask` naturally returns something that lets `AppComponent`'s handler skip the manual `project.specs.push()` (e.g. the sidebar re-reads via `ProjectsService.list()`), take the simpler path.
- **Sidebar output vs existing `action` EventEmitter** — the guide prescribes a new `generateNextTask` output because the payload includes the `Project`. If you discover an existing typed-payload output pattern already in use in the codebase, mirror that; log deviation.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale; thin backend + per-feature Angular service pattern
- [Epic](./epic.md) – Task scope; Task 11 description with edge cases
- [Timeline](./timeline.md) – Status tracking (update to "Done" after verification passes)