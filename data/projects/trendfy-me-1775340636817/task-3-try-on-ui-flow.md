# 🛠️ Task 3: Try-on UI Flow

**Purpose**: Build the user-facing Angular interface where users upload a selfie, select a garment, wait through generation, and view their virtual try-on result.

**Effort**: 1 day

**Dependencies**: Task 1 (Catalog seeding) must be complete to display garments

**Parallel With**: Task 2 (Pipeline orchestration) can be developed simultaneously with mock responses

**Blocks**: Task 4 (End-to-end testing), Task 5 (Landing page)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Selfie upload component with preview
- Garment catalog grid with selection state
- Generation loading state with progress indication
- Result display with download option
- Error handling for failed generations

### What's NOT Included
- User accounts or authentication — frictionless first use
- Generation history — MVP focuses on single session
- Social sharing — post-MVP feature
- Mobile camera capture — file upload only for MVP

---

## Prerequisites

Before starting:
- Angular 19 project initialized with routing
- API service configured to hit `api.trendfy.me` (or localhost:3100 for dev)
- Basic understanding of Angular signals and standalone components
- Catalog API returning garment data (Task 1)

---

## Implementation Steps

### Step 1: Create the Try-on Flow Route Structure

**File**: `src/app/app.routes.ts`

**Purpose**: Set up the route that hosts the try-on experience

```typescript
export const routes: Routes = [
  { path: '', redirectTo: 'try-on', pathMatch: 'full' },
  { 
    path: 'try-on', 
    loadComponent: () => import('./pages/try-on/try-on.component')
      .then(m => m.TryOnComponent) 
  },
];
```

### Step 2: Build the Selfie Upload Component

**File**: `src/app/components/selfie-upload/selfie-upload.component.ts`

**Purpose**: Handle file selection, validation, and preview display

The component accepts image files, validates they're under 10MB, and emits the selected file to the parent. Preview is generated client-side using FileReader.

**Pattern**:
```typescript
@Component({
  selector: 'app-selfie-upload',
  standalone: true,
  template: `
    <div class="upload-zone" 
         [class.has-image]="previewUrl()"
         (dragover)="onDragOver($event)"
         (drop)="onDrop($event)">
      @if (previewUrl()) {
        <img [src]="previewUrl()" alt="Your photo" />
        <button (click)="clear()">Change photo</button>
      } @else {
        <input type="file" accept="image/*" (change)="onFileSelect($event)" />
        <p>Drop your selfie here or click to upload</p>
      }
    </div>
  `
})
export class SelfieUploadComponent {
  previewUrl = signal<string | null>(null);
  fileSelected = output<File>();

  onFileSelect(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file && file.size < 10_000_000) {
      this.generatePreview(file);
      this.fileSelected.emit(file);
    }
  }
}
```

### Step 3: Build the Garment Catalog Grid

**File**: `src/app/components/garment-grid/garment-grid.component.ts`

**Purpose**: Display available garments and track selection state

Fetches garments from the catalog API on init. Single-selection model—clicking a garment deselects any previous selection.

**Pattern**:
```typescript
@Component({
  selector: 'app-garment-grid',
  standalone: true,
  template: `
    <div class="garment-grid">
      @for (garment of garments(); track garment.id) {
        <div class="garment-card" 
             [class.selected]="selectedId() === garment.id"
             (click)="select(garment)">
          <img [src]="garment.imageUrl" [alt]="garment.name" />
          <span>{{ garment.name }}</span>
        </div>
      }
    </div>
  `
})
export class GarmentGridComponent {
  private catalogService = inject(CatalogService);
  
  garments = signal<Garment[]>([]);
  selectedId = signal<string | null>(null);
  garmentSelected = output<Garment>();

  ngOnInit() {
    this.catalogService.getGarments().subscribe(g => this.garments.set(g));
  }

  select(garment: Garment) {
    this.selectedId.set(garment.id);
    this.garmentSelected.emit(garment);
  }
}
```

### Step 4: Create the Generation Loading State

**File**: `src/app/components/generation-loader/generation-loader.component.ts`

**Purpose**: Show progress during the ~65s pipeline execution

The loader displays estimated time remaining and cycles through status messages to keep users engaged. Messages reflect actual pipeline stages from [Architecture](./architecture.md).

**Pattern**:
```typescript
@Component({
  selector: 'app-generation-loader',
  template: `
    <div class="loader-container">
      <div class="spinner"></div>
      <p class="status">{{ currentMessage() }}</p>
      <p class="estimate">~{{ secondsRemaining() }}s remaining</p>
    </div>
  `
})
export class GenerationLoaderComponent {
  private messages = [
    'Analyzing your photo...',
    'Preparing garment...',
    'Generating try-on...',
    'Enhancing result...',
    'Almost there...'
  ];
  
  currentMessage = signal(this.messages[0]);
  secondsRemaining = signal(65);
  
  ngOnInit() {
    // Cycle messages every 12s, countdown every second
    interval(1000).pipe(takeUntilDestroyed()).subscribe(tick => {
      this.secondsRemaining.update(s => Math.max(0, s - 1));
      if (tick % 12 === 0) {
        const idx = Math.min(Math.floor(tick / 12), this.messages.length - 1);
        this.currentMessage.set(this.messages[idx]);
      }
    });
  }
}
```

### Step 5: Build the Result Display Component

**File**: `src/app/components/result-display/result-display.component.ts`

**Purpose**: Show the generated try-on image with download capability

**Pattern**:
```typescript
@Component({
  selector: 'app-result-display',
  template: `
    <div class="result-container">
      <img [src]="resultUrl()" alt="Your try-on result" />
      <div class="actions">
        <button (click)="download()">Download</button>
        <button (click)="tryAnother.emit()">Try another</button>
      </div>
    </div>
  `
})
export class ResultDisplayComponent {
  resultUrl = input.required<string>();
  tryAnother = output<void>();

  download() {
    const link = document.createElement('a');
    link.href = this.resultUrl();
    link.download = 'trendfy-tryon.png';
    link.click();
  }
}
```

### Step 6: Assemble the Try-on Page

**File**: `src/app/pages/try-on/try-on.component.ts`

**Purpose**: Orchestrate the flow between upload → select → generate → result

This is the main container that manages flow state and coordinates child components.

**Pattern**:
```typescript
type FlowState = 'upload' | 'select' | 'generating' | 'result' | 'error';

@Component({
  selector: 'app-try-on',
  standalone: true,
  imports: [SelfieUploadComponent, GarmentGridComponent, GenerationLoaderComponent, ResultDisplayComponent],
  template: `
    <main class="try-on-page">
      @switch (state()) {
        @case ('upload') {
          <h2>Upload your photo</h2>
          <app-selfie-upload (fileSelected)="onSelfieSelected($event)" />
        }
        @case ('select') {
          <h2>Choose a garment</h2>
          <app-garment-grid (garmentSelected)="onGarmentSelected($event)" />
        }
        @case ('generating') {
          <app-generation-loader />
        }
        @case ('result') {
          <app-result-display [resultUrl]="resultUrl()!" (tryAnother)="reset()" />
        }
        @case ('error') {
          <div class="error">
            <p>{{ errorMessage() }}</p>
            <button (click)="reset()">Try again</button>
          </div>
        }
      }
    </main>
  `
})
export class TryOnComponent {
  private tryOnService = inject(TryOnService);

  state = signal<FlowState>('upload');
  selfie = signal<File | null>(null);
  garment = signal<Garment | null>(null);
  resultUrl = signal<string | null>(null);
  errorMessage = signal<string>('');

  onSelfieSelected(file: File) {
    this.selfie.set(file);
    this.state.set('select');
  }

  onGarmentSelected(garment: Garment) {
    this.garment.set(garment);
    this.generate();
  }

  generate() {
    this.state.set('generating');
    this.tryOnService.generate(this.selfie()!, this.garment()!.id)
      .subscribe({
        next: (result) => {
          this.resultUrl.set(result.imageUrl);
          this.state.set('result');
        },
        error: (err) => {
          this.errorMessage.set(err.message || 'Generation failed');
          this.state.set('error');
        }
      });
  }

  reset() {
    this.state.set('upload');
    this.selfie.set(null);
    this.garment.set(null);
    this.resultUrl.set(null);
  }
}
```

### Step 7: Create the Try-on Service

**File**: `src/app/services/try-on.service.ts`

**Purpose**: Handle API communication for generation requests

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class TryOnService {
  private http = inject(HttpClient);
  private apiUrl = environment.apiUrl;

  generate(selfie: File, garmentId: string): Observable<{ imageUrl: string }> {
    const formData = new FormData();
    formData.append('selfie', selfie);
    formData.append('garmentId', garmentId);

    return this.http.post<{ jobId: string }>(`${this.apiUrl}/try-on`, formData)
      .pipe(
        switchMap(({ jobId }) => this.pollForResult(jobId))
      );
  }

  private pollForResult(jobId: string): Observable<{ imageUrl: string }> {
    return interval(3000).pipe(
      switchMap(() => this.http.get<{ status: string; imageUrl?: string }>(
        `${this.apiUrl}/try-on/${jobId}`
      )),
      takeWhile(res => res.status === 'processing', true),
      filter(res => res.status === 'complete'),
      map(res => ({ imageUrl: res.imageUrl! })),
      take(1),
      timeout(120_000) // 2 minute max wait
    );
  }
}
```

---

## Verification

How to verify this implementation works:

```bash
# Start the dev server
npm start

# Open browser to http://localhost:4200/try-on
```

**Manual test flow**:
1. Upload a selfie image → should show preview and advance to garment selection
2. Click a garment → should show loading state
3. Wait for generation → should display result (or mock if Task 2 incomplete)
4. Click "Download" → should download the image
5. Click "Try another" → should reset to upload state

**With mock API** (if Task 2 not ready):
```typescript
// In try-on.service.ts, temporarily return mock data
generate(selfie: File, garmentId: string) {
  return of({ imageUrl: 'https://picsum.photos/512' }).pipe(delay(5000));
}
```

**Expected Result**: Complete flow from upload through result display with no console errors

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 3 as done
2. Integrate with real pipeline API once Task 2 is complete
3. Proceed to Task 4 (End-to-end testing)

---

## Related Documents

- [Architecture](./architecture.md) – Pipeline design and API contracts
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking