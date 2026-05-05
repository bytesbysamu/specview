# 🛠️ Task 5: Live Preview Integration

**Purpose**: Enable real-time visualization of implemented code by embedding the container's dev server output directly in the editor interface.

**Effort**: 1 day

**Dependencies**: Task 3 (Container Management), Task 4 (Basic Agent Execution)

**Parallel With**: —

**Blocks**: Full demo workflow, user testing

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Iframe-based preview panel component
- Container port discovery and URL construction
- Auto-refresh on file change detection
- Loading and error states for preview
- Split view layout with editor and preview

### What's NOT Included
- Hot module replacement (HMR) passthrough — relies on container's native HMR
- Multiple preview tabs — single preview per project for POC
- Mobile viewport simulation — future enhancement

---

## Prerequisites

Before starting:
- Container management service operational (Task 3)
- Agent can create files that trigger dev server updates (Task 4)
- Understanding of Angular's change detection for iframe handling
- Container dev server running on predictable port (3000)

---

## Implementation Steps

### Step 1: Create Preview Panel Component

**File**: `src/app/components/preview-panel/preview-panel.component.ts`

**Purpose**: Encapsulate iframe rendering with loading states and error handling

The preview panel needs to handle three states: loading (container starting), ready (iframe can load), and error (container unreachable). Use a simple state machine rather than multiple boolean flags.

**Pattern**:
```typescript
type PreviewState = 'loading' | 'ready' | 'error' | 'not-started';

@Component({
  selector: 'app-preview-panel',
  template: `
    @switch (state()) {
      @case ('loading') {
        <div class="preview-loading">
          <span class="spinner"></span>
          <p>Starting dev server...</p>
        </div>
      }
      @case ('ready') {
        <iframe 
          [src]="previewUrl() | safe:'resourceUrl'"
          (load)="onIframeLoad()"
          (error)="onIframeError()">
        </iframe>
      }
      @case ('error') {
        <div class="preview-error">
          <p>Preview unavailable</p>
          <button (click)="retry()">Retry</button>
        </div>
      }
      @case ('not-started') {
        <div class="preview-placeholder">
          <p>Run an implementation to see preview</p>
        </div>
      }
    }
  `
})
export class PreviewPanelComponent {
  state = signal<PreviewState>('not-started');
  previewUrl = signal<string>('');
  
  // Inject container service to get port info
}
```

### Step 2: Create Safe Pipe for iframe URLs

**File**: `src/app/pipes/safe.pipe.ts`

**Purpose**: Bypass Angular's security for trusted container URLs

Angular sanitizes URLs by default. Since we control the container URLs, we need to explicitly trust them. Limit this to resourceUrl type only.

**Pattern**:
```typescript
@Pipe({ name: 'safe', standalone: true })
export class SafePipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}
  
  transform(value: string, type: 'resourceUrl'): SafeResourceUrl {
    if (type === 'resourceUrl') {
      return this.sanitizer.bypassSecurityTrustResourceUrl(value);
    }
    throw new Error(`Unsupported safe type: ${type}`);
  }
}
```

### Step 3: Add Port Discovery to Container Service

**File**: `src/app/services/container.service.ts`

**Purpose**: Expose container's mapped port for preview URL construction

The container service already manages container lifecycle. Add a method to retrieve the externally-accessible URL for the dev server.

**Pattern**:
```typescript
// Add to existing ContainerService
getPreviewUrl(containerId: string): string | null {
  const container = this.containers.get(containerId);
  if (!container || container.status !== 'running') {
    return null;
  }
  // Port mapping configured in container creation
  // Container internal 3000 -> host dynamic port
  return `http://localhost:${container.mappedPort}`;
}

// Emit events when container becomes ready
containerReady$ = new Subject<{ containerId: string; previewUrl: string }>();
```

### Step 4: Implement File Change Detection

**File**: `src/app/services/preview.service.ts`

**Purpose**: Coordinate preview refresh when agent modifies files

Rather than polling, subscribe to agent output events that indicate file writes. The dev server's HMR handles the actual refresh—we just need to know when to expect changes.

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class PreviewService {
  private refreshTrigger$ = new Subject<void>();
  
  constructor(
    private agentService: AgentService,
    private containerService: ContainerService
  ) {
    // Listen for file write events from agent
    this.agentService.events$
      .pipe(filter(e => e.type === 'file_write'))
      .subscribe(() => {
        // Small delay to let dev server pick up changes
        setTimeout(() => this.refreshTrigger$.next(), 500);
      });
  }
  
  // Components subscribe to this
  get refresh$() {
    return this.refreshTrigger$.asObservable();
  }
  
  // Force refresh the iframe
  triggerRefresh() {
    this.refreshTrigger$.next();
  }
}
```

### Step 5: Wire Up Preview Panel to Services

**File**: `src/app/components/preview-panel/preview-panel.component.ts`

**Purpose**: Connect component to container and preview services

**Pattern**:
```typescript
export class PreviewPanelComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  private iframeRef = viewChild<ElementRef>('previewFrame');
  
  ngOnInit() {
    // Update state when container becomes ready
    this.containerService.containerReady$
      .pipe(takeUntil(this.destroy$))
      .subscribe(({ previewUrl }) => {
        this.previewUrl.set(previewUrl);
        this.state.set('ready');
      });
    
    // Refresh iframe on file changes
    this.previewService.refresh$
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.refreshIframe());
  }
  
  private refreshIframe() {
    const iframe = this.iframeRef()?.nativeElement as HTMLIFrameElement;
    if (iframe) {
      // Force reload by reassigning src
      const currentSrc = iframe.src;
      iframe.src = '';
      iframe.src = currentSrc;
    }
  }
}
```

### Step 6: Add Split View Layout

**File**: `src/app/components/workspace/workspace.component.ts`

**Purpose**: Arrange editor and preview side-by-side with resizable divider

Reuse the existing split view pattern from the editor/preview layout. The workspace becomes: sidebar | editor | preview.

**Pattern**:
```typescript
@Component({
  template: `
    <div class="workspace">
      <app-sidebar />
      <div class="main-content" [class.with-preview]="showPreview()">
        <div class="editor-area">
          <app-editor />
        </div>
        @if (showPreview()) {
          <div class="resizer" (mousedown)="startResize($event)"></div>
          <div class="preview-area" [style.width.px]="previewWidth()">
            <app-preview-panel />
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .main-content.with-preview {
      display: grid;
      grid-template-columns: 1fr auto minmax(300px, var(--preview-width, 400px));
    }
    .resizer {
      width: 4px;
      cursor: col-resize;
      background: var(--border-color);
    }
  `]
})
```

### Step 7: Handle Container Not-Ready States

**File**: `src/app/components/preview-panel/preview-panel.component.ts`

**Purpose**: Gracefully handle startup delays and connection failures

Containers take time to start. Show progress indicators and retry logic.

**Pattern**:
```typescript
// Add retry logic with exponential backoff
async checkContainerReady(containerId: string, attempt = 1): Promise<boolean> {
  const maxAttempts = 5;
  const url = this.containerService.getPreviewUrl(containerId);
  
  if (!url) {
    if (attempt < maxAttempts) {
      await this.delay(1000 * attempt); // 1s, 2s, 3s...
      return this.checkContainerReady(containerId, attempt + 1);
    }
    return false;
  }
  
  // Verify URL is actually responding
  try {
    await fetch(url, { method: 'HEAD', mode: 'no-cors' });
    return true;
  } catch {
    if (attempt < maxAttempts) {
      await this.delay(1000 * attempt);
      return this.checkContainerReady(containerId, attempt + 1);
    }
    return false;
  }
}
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Start the application
npm run dev

# 2. Create a new project and run an implementation
# (Use existing Task 4 functionality)

# 3. Observe preview panel transitions:
#    - "Starting dev server..." while container boots
#    - Live preview appears when ready
#    - Preview updates when agent writes files
```

**Expected Result**: 
- Preview shows "Starting dev server..." initially
- After 5-15 seconds, live application appears in iframe
- When agent modifies files, preview reflects changes within 1-2 seconds
- Resizer allows adjusting editor/preview split
- Error state shows if container fails with retry option

**Manual Test Checklist**:
- [ ] Preview loads after container starts
- [ ] Iframe refreshes on file changes
- [ ] Loading state displays during startup
- [ ] Error state displays if container unreachable
- [ ] Retry button recovers from error state
- [ ] Split view resizer works
- [ ] Preview hidden when no active implementation

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 5 done
2. Proceed to Task 6: Agent Output Streaming UI
3. Test full workflow: edit spec → run implementation → see preview

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for preview integration
- [Epic](./epic.md) – Task scope and acceptance criteria
- [Timeline](./timeline.md) – Status tracking