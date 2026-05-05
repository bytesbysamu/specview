# 🛠️ Task 1: Garment Detection Pipeline

**Purpose**: Build the ingestion system that transforms outfit photos into individual, tagged garment images—the foundation data layer that all other features depend on.

**Effort**: 3 days

**Dependencies**: None (first task)

**Parallel With**: —

**Blocks**: Task 2 (Closet Management UI), Task 3 (Virtual Try-On Integration)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Clothing segmentation (separate individual garments from outfit photos)
- Background removal for each extracted garment
- Automatic tagging (type, color, style attributes)
- Image storage and metadata persistence
- Processing queue for async handling

### What's NOT Included
- Virtual try-on synthesis — separate task, different infrastructure
- User-facing upload UI — handled in Task 2 (Closet Management)
- Brand/price detection — future enhancement, not MVP

---

## Prerequisites

Before starting:
- Cloud storage bucket configured (S3/GCS/R2)
- Database schema for garments table
- API key for segmentation service (Segment Anything, Remove.bg, or self-hosted)
- Basic understanding of image processing pipelines

---

## Implementation Steps

### Step 1: Define Garment Data Model

**File**: `src/models/garment.ts`

**Purpose**: Establish the data structure that flows through the entire system.

The garment model needs to capture both the image data and the AI-extracted metadata. Keep it flat—nested objects complicate queries later.

**Pattern**:
```typescript
interface Garment {
  id: string;
  userId: string;
  originalImageUrl: string;    // Full outfit photo
  extractedImageUrl: string;   // Individual garment, background removed
  
  // AI-extracted metadata
  type: 'top' | 'bottom' | 'outerwear' | 'footwear' | 'accessory';
  subtype: string;             // "t-shirt", "jeans", "sneakers"
  primaryColor: string;
  secondaryColors: string[];
  pattern: 'solid' | 'striped' | 'plaid' | 'floral' | 'other';
  style: 'casual' | 'formal' | 'athletic' | 'streetwear';
  
  // Processing metadata
  confidence: number;          // 0-1, how confident the detection was
  boundingBox: { x: number; y: number; width: number; height: number };
  createdAt: Date;
  processedAt: Date | null;
  status: 'pending' | 'processing' | 'complete' | 'failed';
}
```

### Step 2: Build Segmentation Service

**File**: `src/services/segmentation.service.ts`

**Purpose**: Extract individual garments from outfit photos using instance segmentation.

This is the core computer vision step. Use a pre-trained model (Segment Anything works well) or a managed API. The key is getting clean masks for each clothing item.

**Pattern**:
```typescript
interface SegmentationResult {
  masks: Array<{
    mask: ImageData;           // Binary mask for this garment
    boundingBox: BoundingBox;
    label: string;             // "shirt", "pants", etc.
    confidence: number;
  }>;
}

class SegmentationService {
  async segmentOutfit(imageBuffer: Buffer): Promise<SegmentationResult> {
    // Option A: Call managed API (Remove.bg, Photoroom)
    // Option B: Self-hosted SAM (Segment Anything Model)
    // Option C: Cloud Vision API with object detection
    
    // Returns array of masks, one per detected garment
  }
  
  async extractGarment(
    originalImage: Buffer, 
    mask: ImageData
  ): Promise<Buffer> {
    // Apply mask to original image
    // Crop to bounding box with padding
    // Return transparent PNG
  }
}
```

**Implementation notes**:
- Start with a managed API (faster to ship), migrate to self-hosted if costs justify
- Add 10-15% padding around bounding boxes—tight crops look unnatural
- Output transparent PNGs at consistent dimensions (e.g., 512x512)

### Step 3: Build Tagging Service

**File**: `src/services/tagging.service.ts`

**Purpose**: Extract clothing attributes from segmented garment images.

Tagging happens after segmentation. The cleaner the input (background removed, single garment), the better the results. Use a vision-language model for flexibility.

**Pattern**:
```typescript
interface TaggingResult {
  type: string;
  subtype: string;
  primaryColor: string;
  secondaryColors: string[];
  pattern: string;
  style: string;
  confidence: number;
}

class TaggingService {
  private readonly prompt = `
    Analyze this clothing item and return JSON with:
    - type: top/bottom/outerwear/footwear/accessory
    - subtype: specific item (t-shirt, jeans, sneakers)
    - primaryColor: dominant color name
    - secondaryColors: array of other colors
    - pattern: solid/striped/plaid/floral/other
    - style: casual/formal/athletic/streetwear
  `;

  async tagGarment(imageBuffer: Buffer): Promise<TaggingResult> {
    // Call vision model (Claude, GPT-4V, Gemini)
    // Parse structured response
    // Validate against known categories
  }
}
```

**Implementation notes**:
- Normalize color names to a fixed palette (CSS color names work well)
- Cache common items—a plain white t-shirt doesn't need re-analysis
- Set confidence threshold (0.7+) before auto-accepting tags

### Step 4: Build Processing Queue

**File**: `src/services/processing-queue.service.ts`

**Purpose**: Handle async processing so uploads feel instant while heavy lifting happens in the background.

Per the [Architecture](./architecture.md), the cheap path (uploads, browsing) must feel instant. Queue the expensive work.

**Pattern**:
```typescript
class ProcessingQueueService {
  async enqueue(job: ProcessingJob): Promise<string> {
    // Add to queue (Redis, SQS, or database-backed)
    // Return job ID for status polling
  }

  async processJob(job: ProcessingJob): Promise<void> {
    // 1. Download original image
    // 2. Run segmentation → get masks
    // 3. For each mask:
    //    a. Extract garment image
    //    b. Upload to storage
    //    c. Run tagging
    //    d. Save garment record
    // 4. Update job status
  }
}

// Job schema
interface ProcessingJob {
  id: string;
  userId: string;
  originalImageUrl: string;
  status: 'pending' | 'processing' | 'complete' | 'failed';
  garmentIds: string[];        // Populated as garments are extracted
  error?: string;
}
```

**Implementation notes**:
- Simple queue: database polling with `status` column works for MVP
- Better queue: Redis + Bull for retries and concurrency control
- Set reasonable timeout (60s)—if segmentation takes longer, something's wrong

### Step 5: Create Processing API Endpoint

**File**: `src/api/garments.controller.ts`

**Purpose**: Accept uploads and expose processing status.

**Pattern**:
```typescript
// POST /api/garments/upload
// Accepts multipart/form-data with outfit image
async uploadOutfit(req: Request, res: Response) {
  const imageBuffer = req.file.buffer;
  
  // 1. Validate image (size, format, dimensions)
  // 2. Upload original to storage
  // 3. Create processing job
  // 4. Return job ID immediately
  
  return res.json({ 
    jobId: job.id,
    status: 'pending',
    statusUrl: `/api/garments/jobs/${job.id}`
  });
}

// GET /api/garments/jobs/:jobId
// Poll for processing status
async getJobStatus(req: Request, res: Response) {
  const job = await this.jobService.getJob(req.params.jobId);
  
  return res.json({
    status: job.status,
    garments: job.garmentIds,    // Garment IDs as they become available
    error: job.error
  });
}
```

### Step 6: Wire Up the Pipeline

**File**: `src/workers/garment-processor.worker.ts`

**Purpose**: Connect all services into a single processing flow.

**Pattern**:
```typescript
class GarmentProcessorWorker {
  constructor(
    private segmentation: SegmentationService,
    private tagging: TaggingService,
    private storage: StorageService,
    private garmentRepo: GarmentRepository
  ) {}

  async process(job: ProcessingJob): Promise<Garment[]> {
    const originalImage = await this.storage.download(job.originalImageUrl);
    
    // Segment outfit into individual garments
    const segments = await this.segmentation.segmentOutfit(originalImage);
    
    const garments: Garment[] = [];
    
    for (const segment of segments.masks) {
      // Extract individual garment
      const garmentImage = await this.segmentation.extractGarment(
        originalImage, 
        segment.mask
      );
      
      // Upload extracted image
      const extractedUrl = await this.storage.upload(
        garmentImage,
        `garments/${job.userId}/${uuid()}.png`
      );
      
      // Tag the garment
      const tags = await this.tagging.tagGarment(garmentImage);
      
      // Persist
      const garment = await this.garmentRepo.create({
        userId: job.userId,
        originalImageUrl: job.originalImageUrl,
        extractedImageUrl: extractedUrl,
        boundingBox: segment.boundingBox,
        confidence: segment.confidence,
        ...tags
      });
      
      garments.push(garment);
    }
    
    return garments;
  }
}
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Upload a test outfit photo
curl -X POST http://localhost:3100/api/garments/upload \
  -F "image=@test-outfit.jpg" \
  -H "Authorization: Bearer $TOKEN"

# Expected: { "jobId": "abc123", "status": "pending" }

# 2. Poll for completion
curl http://localhost:3100/api/garments/jobs/abc123

# Expected after processing:
# { 
#   "status": "complete", 
#   "garments": ["g1", "g2", "g3"]
# }

# 3. Verify garment data
curl http://localhost:3100/api/garments/g1

# Expected:
# {
#   "id": "g1",
#   "type": "top",
#   "subtype": "t-shirt",
#   "primaryColor": "navy",
#   "extractedImageUrl": "https://storage.../garments/..."
# }
```

**Expected Result**: 
- Outfit photo with 3 items → 3 separate garment records
- Each garment has transparent background, correct type/color tags
- Processing completes in under 30 seconds for typical photos

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 1 complete
2. Proceed to Task 2 (Closet Management UI) — can now display garments
3. Task 3 (Virtual Try-On) becomes unblocked

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for the fast/slow path split
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking