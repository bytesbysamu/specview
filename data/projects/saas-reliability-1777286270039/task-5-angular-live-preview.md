# Task 5: Angular Live Preview, Cancel, Regenerate

**Effort**: 0.3 days

## Overview

Render the new fields exposed by [Task 4](./task-4-retry-cancel-routes.md) — `current_step`, `partial`, `warnings`, `error` — in the Angular new-project component. Add three UI elements: a `<pre>` block showing the rolling streaming tail, a red Cancel button next to the spinner that flips to "Cancelling…" until status flips to `CANCELLED`, and a Regenerate button on any spec file with `size === 0`, `warnings.length > 0`, or `error != null`. Existing 3-second polling already drives all four; only the rendering layer changes. See [Solution Architecture](./architecture.md) § Component Design.

This task does not introduce a new HTTP service — `AiService.bootstrapStatus()` already polls the same endpoint; the response shape is wider after Task 4 and the component reads the new fields directly.

## Prerequisites

- [Task 4](./task-4-retry-cancel-routes.md) merged — the polling response carries `current_step`, `partial`, `warnings`, `error`; cancel and retry routes return 202
- `{WORKSPACE}/web/src/app/components/new-project/new-project.component.ts` exists and uses the existing `AiService.bootstrapStatus()` 3-second poll loop
- `{WORKSPACE}/web/src/app/services/ai.service.ts` exposes `bootstrapStatus(jobId)` and `bootstrapProject(req)` returning typed Observables
- Angular 17 standalone-components stack with signals (per `versions.md`)

Run from `{WORKSPACE}/web/`:

```bash
git status
ng build --configuration development 2>&1 | tail -10
ls src/app/components/new-project/
ls src/app/services/
```

## Implementation Steps

### Step 1: Add cancel and retry methods to AiService

**File**: `{WORKSPACE}/web/src/app/services/ai.service.ts`

Add the two new methods alongside the existing `bootstrapStatus`:

```typescript
cancelBootstrap(jobId: string) {
  return this.http.post<{status: string}>(
    `${this.baseUrl}/bootstrap-project/${jobId}/cancel`, {},
  );
}

retryBootstrap(jobId: string, step: 'analysis' | 'epic' | 'architecture') {
  return this.http.post<{job_id: string}>(
    `${this.baseUrl}/bootstrap-project/${jobId}/retry`, { step },
  );
}
```

`baseUrl` is the existing `/api/ai/text` constant on the service. If your file uses a different base path, substitute the same one used by `bootstrapStatus`.

### Step 2: Extend the polling response type

**File**: `{WORKSPACE}/web/src/app/services/ai.service.ts`

Update the existing response interface for `bootstrapStatus` to include the four new fields. If you have not declared an interface, add one:

```typescript
export interface BootstrapStatusResponse {
  running: boolean;
  done: boolean;
  current_step: string | null;
  partial: string;
  warnings: string[];
  error?: string;
  status?: 'cancelled';
  files?: Array<{ filename: string; content: string }>;
  latencyMs?: number;
}
```

Update the `bootstrapStatus` method's return type to `Observable<BootstrapStatusResponse>`.

### Step 3: Render live preview, cancel button, and regenerate buttons in the component

**File**: `{WORKSPACE}/web/src/app/components/new-project/new-project.component.ts`

Add three signals to track the new state. Read them inside the existing 3-second poll subscription:

```typescript
import { signal, computed } from '@angular/core';

// inside the component class
currentStep = signal<string | null>(null);
partial = signal<string>('');
warnings = signal<string[]>([]);
cancelling = signal<boolean>(false);
jobId = signal<string | null>(null);

isCancellable = computed(() =>
  !!this.jobId() && !this.cancelling() && this.currentStep() !== null,
);
```

Inside the existing poll subscription, after parsing the response, set the new signals:

```typescript
// existing subscribe handler
this.ai.bootstrapStatus(jobId).subscribe((res) => {
  this.currentStep.set(res.current_step);
  this.partial.set(res.partial ?? '');
  this.warnings.set(res.warnings ?? []);
  if (res.done) {
    // ... existing done handling: surface res.files, res.error, etc.
  }
});
```

Add the cancel handler:

```typescript
onCancel() {
  const id = this.jobId();
  if (!id) return;
  this.cancelling.set(true);
  this.ai.cancelBootstrap(id).subscribe({
    next: () => { /* runtime flips to CANCELLED on next poll */ },
    error: () => this.cancelling.set(false),
  });
}
```

Add the regenerate handler:

```typescript
onRegenerate(step: 'analysis' | 'epic' | 'architecture') {
  const id = this.jobId();
  if (!id) return;
  this.ai.retryBootstrap(id, step).subscribe((res) => {
    this.jobId.set(res.job_id);
    this.cancelling.set(false);
    // existing poll loop will pick up the new job_id automatically
  });
}
```

### Step 4: Wire the template

**File**: `{WORKSPACE}/web/src/app/components/new-project/new-project.component.ts` (template — inline or `.html`)

Add to the existing template, between the spinner and the result block:

```html
<!-- Live streaming preview -->
@if (currentStep(); as step) {
  <div class="bootstrap-progress">
    <p>Generating <strong>{{ step }}</strong>...</p>
    @if (partial()) {
      <pre class="partial-preview">{{ partial() }}</pre>
    }
    <button
      type="button"
      class="cancel-btn"
      [disabled]="cancelling() || !isCancellable()"
      (click)="onCancel()">
      {{ cancelling() ? 'Cancelling...' : 'Cancel' }}
    </button>
  </div>
}

<!-- Warnings (render whenever non-empty) -->
@if (warnings().length > 0) {
  <ul class="bootstrap-warnings">
    @for (w of warnings(); track w) {
      <li>{{ w }}</li>
    }
  </ul>
}

<!-- Per-file regenerate buttons -->
@for (file of bootstrapFiles(); track file.filename) {
  <div class="file-row">
    <span>{{ file.filename }}</span>
    @if (
      file.content.length === 0
      || warnings().length > 0
      || lastError()
    ) {
      <button
        type="button"
        class="regenerate-btn"
        (click)="onRegenerate(stepForFile(file.filename))">
        Regenerate
      </button>
    }
  </div>
}
```

Add the helper that maps a filename back to a sub-workflow step name:

```typescript
stepForFile(filename: string): 'analysis' | 'epic' | 'architecture' {
  if (filename.startsWith('analysis')) return 'analysis';
  if (filename.startsWith('epic')) return 'epic';
  return 'architecture';
}

lastError = signal<string | null>(null);
bootstrapFiles = signal<Array<{ filename: string; content: string }>>([]);
```

Inside the poll subscription's `done` branch, populate `lastError` from `res.error` and `bootstrapFiles` from `res.files`.

### Step 5: Add minimal styles

**File**: `{WORKSPACE}/web/src/app/components/new-project/new-project.component.ts` (or `.scss` if external)

```scss
.bootstrap-progress {
  margin: 1rem 0;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.partial-preview {
  max-height: 12rem;
  overflow: auto;
  padding: 0.5rem;
  background: #f7f7f7;
  font-family: monospace;
  font-size: 0.85rem;
  white-space: pre-wrap;
  word-break: break-word;
}
.cancel-btn {
  background: #c0392b;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
}
.cancel-btn:disabled {
  background: #888;
  cursor: not-allowed;
}
.bootstrap-warnings {
  background: #fff3cd;
  border: 1px solid #ffeeba;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.9rem;
}
.regenerate-btn {
  margin-left: 1rem;
  padding: 0.3rem 0.6rem;
  border: 1px solid #aaa;
  background: white;
  cursor: pointer;
  border-radius: 4px;
}
```

## Tests

**File**: `{WORKSPACE}/web/src/app/components/new-project/new-project.component.spec.ts` (extend existing or create)

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { NewProjectComponent } from './new-project.component';
import { AiService } from '../../services/ai.service';
import { of, throwError } from 'rxjs';

describe('NewProjectComponent — reliability surface', () => {
  let fixture: ComponentFixture<NewProjectComponent>;
  let component: NewProjectComponent;
  let ai: jasmine.SpyObj<AiService>;

  beforeEach(async () => {
    ai = jasmine.createSpyObj<AiService>('AiService', [
      'bootstrapProject', 'bootstrapStatus', 'cancelBootstrap', 'retryBootstrap',
    ]);

    await TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, NewProjectComponent],
      providers: [{ provide: AiService, useValue: ai }],
    }).compileComponents();

    fixture = TestBed.createComponent(NewProjectComponent);
    component = fixture.componentInstance;
  });

  it('renders partial preview when current_step and partial are set', () => {
    component.currentStep.set('architecture');
    component.partial.set('streaming tail text');
    fixture.detectChanges();

    const html = fixture.nativeElement.textContent as string;
    expect(html).toContain('architecture');
    expect(html).toContain('streaming tail text');
  });

  it('cancel button calls AiService.cancelBootstrap and flips cancelling signal', () => {
    ai.cancelBootstrap.and.returnValue(of({ status: 'CANCELLING' }));
    component.jobId.set('job-x');
    component.currentStep.set('epic');

    component.onCancel();

    expect(ai.cancelBootstrap).toHaveBeenCalledWith('job-x');
    expect(component.cancelling()).toBeTrue();
  });

  it('cancel error resets cancelling signal', () => {
    ai.cancelBootstrap.and.returnValue(throwError(() => new Error('boom')));
    component.jobId.set('job-y');
    component.currentStep.set('analysis');

    component.onCancel();

    expect(component.cancelling()).toBeFalse();
  });

  it('regenerate calls AiService.retryBootstrap and adopts new job_id', () => {
    ai.retryBootstrap.and.returnValue(of({ job_id: 'new-job-1' }));
    component.jobId.set('old-job-0');

    component.onRegenerate('architecture');

    expect(ai.retryBootstrap).toHaveBeenCalledWith('old-job-0', 'architecture');
    expect(component.jobId()).toBe('new-job-1');
  });

  it('stepForFile maps filenames to sub-workflow step names', () => {
    expect(component.stepForFile('analysis.md')).toBe('analysis');
    expect(component.stepForFile('epic.md')).toBe('epic');
    expect(component.stepForFile('architecture.md')).toBe('architecture');
    expect(component.stepForFile('README.md')).toBe('architecture'); // fallback
  });

  it('warnings list renders one <li> per warning', () => {
    component.warnings.set([
      'unclosed_code_fence: 3 triple-backticks (odd)',
      'missing_terminal_newline',
    ]);
    fixture.detectChanges();

    const items = fixture.nativeElement.querySelectorAll('.bootstrap-warnings li');
    expect(items.length).toBe(2);
    expect(items[0].textContent).toContain('unclosed_code_fence');
    expect(items[1].textContent).toContain('missing_terminal_newline');
  });

  it('isCancellable is false when no jobId is set', () => {
    component.jobId.set(null);
    expect(component.isCancellable()).toBeFalse();
  });

  it('isCancellable is true when jobId is set, currentStep is set, and not cancelling', () => {
    component.jobId.set('job-z');
    component.currentStep.set('analysis');
    component.cancelling.set(false);
    expect(component.isCancellable()).toBeTrue();
  });
});
```

Verify in isolation from `{WORKSPACE}/web/`:

```bash
ng test --watch=false --browsers=ChromeHeadless
```

The eight new specs above must pass; existing component specs must remain green.

## Verification

Run from `{WORKSPACE}/web/`:

```bash
ng build --configuration production
```

Build must succeed with no new TypeScript errors.

```bash
ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -20
```

Expected delta: **M → M+8 passing** (eight new component specs; zero existing specs broken). Record the pre-task baseline as M before edits.

Manual smoke-test from `{WORKSPACE}/`:

```bash
make dev   # both Flask :3101 and Angular :4201
```

In a browser, navigate to the new-project page, paste a brain dump, click Bootstrap. The `<pre class="partial-preview">` block must populate within 3 seconds of the architecture step starting. Click Cancel during the architecture step; the button must flip to "Cancelling..." and within at most one step duration the spinner stops. Click Regenerate on the architecture file; a fresh `job_id` must be issued and the poll loop must resume.

```bash
cd {WORKSPACE}
make lint   # web lint
```

Confirms: tslint / eslint clean.

---
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
