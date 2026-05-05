# 🛠️ Task 4: Virtual Try-On Integration

**Purpose**: Wire up the virtual try-on model to generate photorealistic images of users wearing selected garments, enabling the core "magic moment" of the application.

**Effort**: 4 days

**Dependencies**: Task 1 (Photo upload & garment detection), Task 2 (Closet management UI), Task 3 (Person photo capture)

**Parallel With**: —

**Blocks**: Task 5 (Outfit suggestions), Task 6 (Style history)

**Related**:
- [Architecture](./architecture.md) — GPU pipeline design, model selection rationale
- [Epic](./epic.md) — Feature scope and success criteria

---

## Overview

### What's Included
- VTON model integration (OOTDiffusion recommended for permissive licensing)
- Multi-garment selection interface (1-3 items)
- Job queue system for GPU workloads
- Generation progress UI with status updates
- Result display with save/share options

### What's NOT Included
- Model training or fine-tuning — using pre-trained weights
- Real-time generation — 15-35 second latency is acceptable per architecture
- Batch processing — single user requests only for MVP
- Style transfer or color adjustments — raw model output only

---

## Prerequisites

Before starting:
- GPU-enabled inference environment (CUDA 11.8+, 12GB+ VRAM)
- OOTDiffusion or CatVTON model weights downloaded
- Person reference photo system functional (Task 3)
- Garment images stored with segmentation masks (Task 1)
- Redis or similar for job queue management

---

## Implementation Steps

### Step 1: Set Up VTON Model Server

**File**: `services/vton/server.py`

**Purpose**: Create isolated GPU service that handles try-on inference requests

The VTON model runs as a separate service to isolate GPU dependencies and allow independent scaling. This follows the architecture's principle of keeping "the expensive path as narrow as possible."

**Pattern**:
```python
from fastapi import FastAPI, BackgroundTasks
from ootd_inference import OOTDiffusionPipeline
import torch

app = FastAPI()
pipeline = None

@app.on_event("startup")
async def load_model():
    global pipeline
    pipeline = OOTDiffusionPipeline.from_pretrained(
        "levihsu/OOTDiffusion",
        torch_dtype=torch.float16
    ).to("cuda")

@app.post("/generate")
async def generate_tryon(
    person_image: bytes,
    garment_images: list[bytes],  # 1-3 items
    job_id: str
):
    # Validate inputs, queue job, return immediately
    # Actual generation happens in worker
    pass
```

### Step 2: Implement Job Queue System

**File**: `services/api/queues/vton_queue.py`

**Purpose**: Manage async GPU jobs with status tracking and timeout handling

GPU inference takes 15-35 seconds — too long for synchronous HTTP. The queue decouples request submission from result retrieval.

**Pattern**:
```python
from redis import Redis
from rq import Queue
import uuid

redis_conn = Redis()
vton_queue = Queue('vton', connection=redis_conn)

def submit_tryon_job(user_id: str, person_image_id: str, garment_ids: list[str]) -> str:
    job_id = str(uuid.uuid4())
    
    job = vton_queue.enqueue(
        'workers.vton_worker.generate',
        job_id=job_id,
        kwargs={
            'person_image_id': person_image_id,
            'garment_ids': garment_ids,
            'user_id': user_id
        },
        job_timeout=120,  # 2 min max
        result_ttl=3600   # Keep result 1 hour
    )
    
    return job_id

def get_job_status(job_id: str) -> dict:
    job = vton_queue.fetch_job(job_id)
    return {
        'status': job.get_status(),  # queued, started, finished, failed
        'progress': job.meta.get('progress', 0),
        'result_url': job.result if job.is_finished else None
    }
```

### Step 3: Build Garment Compositing Logic

**File**: `services/vton/compositor.py`

**Purpose**: Prepare multi-garment inputs for the model

When users select 2-3 items, we need to layer them appropriately (e.g., shirt under jacket). The model processes one layer at a time with intermediate outputs.

**Pattern**:
```python
LAYER_ORDER = ['bottom', 'top', 'outerwear', 'accessory']

def order_garments(garments: list[dict]) -> list[dict]:
    """Sort garments by layer for sequential try-on"""
    return sorted(garments, key=lambda g: LAYER_ORDER.index(g['category']))

async def composite_sequential(person_image: Image, garments: list[dict], pipeline) -> Image:
    """Apply garments one at a time, using previous output as next input"""
    current = person_image
    ordered = order_garments(garments)
    
    for i, garment in enumerate(ordered):
        yield {'progress': (i / len(ordered)) * 100, 'stage': f'Applying {garment["name"]}'}
        
        current = await pipeline.generate(
            person=current,
            garment=garment['image'],
            mask=garment['mask']
        )
    
    return current
```

### Step 4: Create Selection UI Component

**File**: `src/app/components/tryon-selector/tryon-selector.component.ts`

**Purpose**: Let users pick 1-3 garments from their closet for try-on

**Pattern**:
```typescript
@Component({
  selector: 'app-tryon-selector',
  template: `
    <div class="closet-grid">
      @for (garment of closetItems; track garment.id) {
        <div 
          class="garment-card"
          [class.selected]="isSelected(garment.id)"
          (click)="toggleSelection(garment)">
          <img [src]="garment.thumbnailUrl" [alt]="garment.name" />
          <span class="selection-badge" *ngIf="isSelected(garment.id)">
            {{ getSelectionOrder(garment.id) }}
          </span>
        </div>
      }
    </div>
    
    <button 
      [disabled]="selectedCount === 0 || selectedCount > 3 || isGenerating"
      (click)="startTryOn()">
      Try On {{ selectedCount }} Item(s)
    </button>
  `
})
export class TryonSelectorComponent {
  selectedGarments: Map<string, number> = new Map(); // id -> selection order
  maxSelections = 3;
  
  toggleSelection(garment: Garment): void {
    if (this.selectedGarments.has(garment.id)) {
      this.selectedGarments.delete(garment.id);
    } else if (this.selectedGarments.size < this.maxSelections) {
      this.selectedGarments.set(garment.id, this.selectedGarments.size + 1);
    }
  }
}
```

### Step 5: Implement Generation Progress UI

**File**: `src/app/components/generation-progress/generation-progress.component.ts`

**Purpose**: Show real-time status during the 15-35 second generation

Users need feedback during the wait. Poll job status every 2 seconds and display progress stages.

**Pattern**:
```typescript
@Component({
  selector: 'app-generation-progress',
  template: `
    <div class="progress-modal" *ngIf="isGenerating">
      <div class="progress-ring">
        <svg><!-- Animated ring at progress % --></svg>
      </div>
      <p class="stage">{{ currentStage }}</p>
      <p class="estimate">{{ estimatedRemaining }}</p>
    </div>
  `
})
export class GenerationProgressComponent implements OnDestroy {
  @Input() jobId: string;
  @Output() completed = new EventEmitter<string>();
  
  private pollInterval: Subscription;
  
  ngOnInit(): void {
    this.pollInterval = interval(2000).pipe(
      switchMap(() => this.vtonService.getJobStatus(this.jobId)),
      takeWhile(status => status.status !== 'finished' && status.status !== 'failed', true)
    ).subscribe(status => {
      this.progress = status.progress;
      this.currentStage = status.stage;
      
      if (status.status === 'finished') {
        this.completed.emit(status.result_url);
      }
    });
  }
}
```

### Step 6: Add Result Display and Actions

**File**: `src/app/components/tryon-result/tryon-result.component.ts`

**Purpose**: Display generated image with save/share/regenerate options

**Pattern**:
```typescript
@Component({
  selector: 'app-tryon-result',
  template: `
    <div class="result-container">
      <img [src]="resultImageUrl" alt="Try-on result" class="result-image" />
      
      <div class="actions">
        <button (click)="saveToHistory()">Save to History</button>
        <button (click)="shareResult()">Share</button>
        <button (click)="regenerate()">Try Again</button>
        <button (click)="close()">Close</button>
      </div>
      
      <div class="garments-used">
        <span>Items in this look:</span>
        @for (garment of usedGarments; track garment.id) {
          <img [src]="garment.thumbnailUrl" class="mini-thumb" />
        }
      </div>
    </div>
  `
})
export class TryonResultComponent {
  @Input() resultImageUrl: string;
  @Input() usedGarments: Garment[];
  
  async saveToHistory(): Promise<void> {
    await this.historyService.saveOutfit({
      imageUrl: this.resultImageUrl,
      garmentIds: this.usedGarments.map(g => g.id),
      createdAt: new Date()
    });
  }
}
```

### Step 7: Wire Up API Endpoints

**File**: `services/api/routes/tryon.py`

**Purpose**: REST endpoints connecting frontend to VTON service

**Pattern**:
```python
from fastapi import APIRouter, Depends
from auth import get_current_user

router = APIRouter(prefix="/api/tryon")

@router.post("/generate")
async def start_generation(
    request: TryonRequest,
    user = Depends(get_current_user)
):
    # Validate user has person photo
    person_photo = await get_user_person_photo(user.id)
    if not person_photo:
        raise HTTPException(400, "Upload a reference photo first")
    
    # Validate garment count
    if not 1 <= len(request.garment_ids) <= 3:
        raise HTTPException(400, "Select 1-3 garments")
    
    job_id = submit_tryon_job(
        user_id=user.id,
        person_image_id=person_photo.id,
        garment_ids=request.garment_ids
    )
    
    return {"job_id": job_id}

@router.get("/status/{job_id}")
async def check_status(job_id: str, user = Depends(get_current_user)):
    status = get_job_status(job_id)
    return status
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Start VTON model server
cd services/vton && python server.py

# 2. Start Redis for job queue
redis-server

# 3. Start RQ worker
rq worker vton

# 4. Start API server
cd services/api && uvicorn main:app --reload

# 5. Run integration test
pytest tests/integration/test_tryon_flow.py -v
```

**Manual Test Flow**:
1. Upload a reference photo (Task 3)
2. Add at least one garment to closet (Task 1)
3. Navigate to Try-On screen
4. Select 1-3 garments
5. Click "Try On"
6. Wait for progress to complete (15-35 seconds)
7. Verify result shows user wearing selected items

**Expected Result**: 
- Generation completes without timeout
- Result image is photorealistic
- Garments appear correctly layered
- Save to history works

---

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| CUDA out of memory | Model too large for GPU | Use `torch.float16`, reduce batch size to 1 |
| Generation timeout | GPU overloaded | Check queue length, scale workers |
| Garment misalignment | Poor segmentation mask | Re-run garment detection (Task 1) |
| Black/corrupted output | Input image format issue | Ensure RGB, resize to model input size |

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 4 done
2. Proceed to Task 5 (Outfit suggestions) which builds on try-on capability
3. Gather early user feedback on generation quality

---

## Related Documents

- [Architecture](./architecture.md) — GPU pipeline design, cost considerations
- [Epic](./epic.md) — Task scope and "magic moment" context
- [Timeline](./timeline.md) — Status tracking