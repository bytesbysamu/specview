# 🛠️ Task 2: AI Pipeline Integration

**Purpose**: Wire up the complete AI generation chain—from garment extraction through face enhancement—creating the technical core that transforms a user photo + garment into a realistic try-on result.

**Effort**: 2 days

**Dependencies**: Task 1 (Project scaffold with API routes and service structure)

**Parallel With**: Task 3 (Database schema) can start after Step 2

**Blocks**: Task 4 (Frontend upload flow), Task 5 (Results gallery)

**Related**:
- [Architecture](./architecture.md) — Pipeline design rationale
- [Epic](./epic.md) — Task scope and success criteria

---

## Overview

### What's Included
- Remove.bg integration for background/garment extraction
- Claude Vision integration for garment type detection
- IDM-VTON integration via Replicate for try-on synthesis
- ESRGAN integration for 4x upscaling
- CodeFormer integration for face enhancement
- Pipeline orchestrator that chains all steps
- Error handling and retry logic per step

### What's NOT Included
- Queue management — handled in Task 6
- Cost tracking/billing — separate task
- Caching layer — optimization for later
- Parallel pipeline execution — v2 enhancement

---

## Prerequisites

Before starting:
- Replicate account with API token
- Remove.bg API key
- Claude API key (Anthropic)
- Understanding of async/await patterns in your backend language
- Task 1 complete (Express routes, service structure)

---

## Implementation Steps

### Step 1: Create Pipeline Configuration

**File**: `api/config/pipeline.config.ts`

**Purpose**: Centralize all external API configuration and model versions

Keep model versions explicit. When Replicate updates IDM-VTON, you want to control when you adopt it.

**Pattern**:
```typescript
export const pipelineConfig = {
  removeBg: {
    apiUrl: 'https://api.remove.bg/v1.0/removebg',
    timeout: 30000,
  },
  claude: {
    model: 'claude-sonnet-4-20250514',
    maxTokens: 256,
  },
  replicate: {
    idmVton: {
      model: 'cuuupid/idm-vton',
      version: 'c871bb9b046607b680449ecbae55fd8c6d945e0a1948644bf2361b3d021d3ff4',
    },
    esrgan: {
      model: 'nightmareai/real-esrgan',
      version: '42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b',
    },
    codeformer: {
      model: 'sczhou/codeformer',
      version: '7de2ea26c616d5bf2245ad0d5e24f0ff9a6204578a5c876db53142edd9d2cd56',
    },
  },
  timeouts: {
    generation: 120000,  // IDM-VTON can take 60s+
    upscale: 60000,
    enhance: 60000,
  },
};
```

### Step 2: Implement Individual Pipeline Steps

**File**: `api/services/pipeline/steps/`

**Purpose**: Each AI operation as an isolated, testable function

Create one file per step. Each follows the same interface: takes input, returns output or throws.

**Pattern** (remove-bg.step.ts):
```typescript
import { pipelineConfig } from '@/config/pipeline.config';

interface RemoveBgResult {
  imageBase64: string;
  originalSize: { width: number; height: number };
}

export async function extractGarment(imageUrl: string): Promise<RemoveBgResult> {
  const response = await fetch(pipelineConfig.removeBg.apiUrl, {
    method: 'POST',
    headers: {
      'X-Api-Key': process.env.REMOVEBG_API_KEY!,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      image_url: imageUrl,
      size: 'auto',
      format: 'png',
      type: 'product',  // Optimized for clothing
    }),
    signal: AbortSignal.timeout(pipelineConfig.removeBg.timeout),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new PipelineStepError('remove-bg', error.errors?.[0]?.title || 'Extraction failed');
  }

  const imageBuffer = await response.arrayBuffer();
  return {
    imageBase64: Buffer.from(imageBuffer).toString('base64'),
    originalSize: parseImageDimensions(response.headers),
  };
}
```

**Pattern** (garment-detection.step.ts):
```typescript
import Anthropic from '@anthropic-ai/sdk';
import { pipelineConfig } from '@/config/pipeline.config';

type GarmentType = 'upper_body' | 'lower_body' | 'dresses';

export async function detectGarmentType(imageBase64: string): Promise<GarmentType> {
  const client = new Anthropic();
  
  const response = await client.messages.create({
    model: pipelineConfig.claude.model,
    max_tokens: pipelineConfig.claude.maxTokens,
    messages: [{
      role: 'user',
      content: [
        {
          type: 'image',
          source: { type: 'base64', media_type: 'image/png', data: imageBase64 },
        },
        {
          type: 'text',
          text: `Classify this garment into exactly one category. Respond with ONLY the category name, nothing else.

Categories:
- upper_body: shirts, t-shirts, blouses, jackets, sweaters, tops
- lower_body: pants, jeans, shorts, skirts
- dresses: dresses, jumpsuits, rompers, full-body garments

Category:`,
        },
      ],
    }],
  });

  const result = (response.content[0] as { text: string }).text.trim().toLowerCase();
  
  if (!['upper_body', 'lower_body', 'dresses'].includes(result)) {
    throw new PipelineStepError('garment-detection', `Unknown garment type: ${result}`);
  }
  
  return result as GarmentType;
}
```

**Pattern** (tryon-generation.step.ts):
```typescript
import Replicate from 'replicate';
import { pipelineConfig } from '@/config/pipeline.config';

interface TryOnInput {
  humanImageUrl: string;
  garmentImageBase64: string;
  garmentType: 'upper_body' | 'lower_body' | 'dresses';
}

export async function generateTryOn(input: TryOnInput): Promise<string> {
  const replicate = new Replicate();
  
  const output = await replicate.run(
    `${pipelineConfig.replicate.idmVton.model}:${pipelineConfig.replicate.idmVton.version}`,
    {
      input: {
        human_img: input.humanImageUrl,
        garm_img: `data:image/png;base64,${input.garmentImageBase64}`,
        category: input.garmentType,
        denoise_steps: 30,
        seed: Math.floor(Math.random() * 1000000),
      },
    }
  );

  // Replicate returns URL to generated image
  if (!output || typeof output !== 'string') {
    throw new PipelineStepError('tryon-generation', 'No output from IDM-VTON');
  }

  return output;
}
```

**Pattern** (upscale.step.ts):
```typescript
export async function upscaleImage(imageUrl: string): Promise<string> {
  const replicate = new Replicate();
  
  const output = await replicate.run(
    `${pipelineConfig.replicate.esrgan.model}:${pipelineConfig.replicate.esrgan.version}`,
    {
      input: {
        image: imageUrl,
        scale: 4,
        face_enhance: false,  // We use CodeFormer separately
      },
    }
  );

  return output as string;
}
```

**Pattern** (face-enhance.step.ts):
```typescript
export async function enhanceFace(imageUrl: string): Promise<string> {
  const replicate = new Replicate();
  
  const output = await replicate.run(
    `${pipelineConfig.replicate.codeformer.model}:${pipelineConfig.replicate.codeformer.version}`,
    {
      input: {
        image: imageUrl,
        upscale: 1,  // Already upscaled by ESRGAN
        face_upsample: true,
        background_enhance: false,
        codeformer_fidelity: 0.7,  // Balance between enhancement and original
      },
    }
  );

  return output as string;
}
```

### Step 3: Create Pipeline Orchestrator

**File**: `api/services/pipeline/orchestrator.ts`

**Purpose**: Chain all steps with progress tracking and error boundaries

The orchestrator owns the execution order and progress reporting. Each step is wrapped for consistent error handling.

**Pattern**:
```typescript
import { extractGarment } from './steps/remove-bg.step';
import { detectGarmentType } from './steps/garment-detection.step';
import { generateTryOn } from './steps/tryon-generation.step';
import { upscaleImage } from './steps/upscale.step';
import { enhanceFace } from './steps/face-enhance.step';

type PipelineStep = 'extract' | 'detect' | 'generate' | 'upscale' | 'enhance' | 'complete';

interface PipelineResult {
  finalImageUrl: string;
  intermediateUrls: {
    garmentExtracted: string;
    tryonGenerated: string;
    upscaled: string;
  };
  garmentType: string;
  timing: Record<PipelineStep, number>;
}

type ProgressCallback = (step: PipelineStep, progress: number) => void;

export async function runTryOnPipeline(
  userImageUrl: string,
  garmentImageUrl: string,
  onProgress?: ProgressCallback
): Promise<PipelineResult> {
  const timing: Record<string, number> = {};
  const mark = (step: string) => { timing[step] = Date.now(); };
  
  // Step 1: Extract garment from background
  onProgress?.('extract', 0);
  mark('extract');
  const { imageBase64: garmentBase64 } = await extractGarment(garmentImageUrl);
  
  // Step 2: Detect garment type for IDM-VTON
  onProgress?.('detect', 15);
  mark('detect');
  const garmentType = await detectGarmentType(garmentBase64);
  
  // Step 3: Generate try-on (longest step, ~60s)
  onProgress?.('generate', 25);
  mark('generate');
  const tryonUrl = await generateTryOn({
    humanImageUrl: userImageUrl,
    garmentImageBase64: garmentBase64,
    garmentType,
  });
  
  // Step 4: Upscale result
  onProgress?.('upscale', 70);
  mark('upscale');
  const upscaledUrl = await upscaleImage(tryonUrl);
  
  // Step 5: Enhance face
  onProgress?.('enhance', 85);
  mark('enhance');
  const finalUrl = await enhanceFace(upscaledUrl);
  
  onProgress?.('complete', 100);
  mark('complete');
  
  return {
    finalImageUrl: finalUrl,
    intermediateUrls: {
      garmentExtracted: `data:image/png;base64,${garmentBase64}`,
      tryonGenerated: tryonUrl,
      upscaled: upscaledUrl,
    },
    garmentType,
    timing: calculateDurations(timing),
  };
}

function calculateDurations(marks: Record<string, number>): Record<PipelineStep, number> {
  const steps: PipelineStep[] = ['extract', 'detect', 'generate', 'upscale', 'enhance', 'complete'];
  const durations: Record<string, number> = {};
  
  for (let i = 1; i < steps.length; i++) {
    durations[steps[i - 1]] = marks[steps[i]] - marks[steps[i - 1]];
  }
  
  return durations as Record<PipelineStep, number>;
}
```

### Step 4: Add Error Types and Retry Logic

**File**: `api/services/pipeline/errors.ts`

**Purpose**: Consistent error handling with retryable vs fatal distinction

**Pattern**:
```typescript
export class PipelineStepError extends Error {
  constructor(
    public readonly step: string,
    message: string,
    public readonly retryable: boolean = false,
    public readonly cause?: unknown
  ) {
    super(`[${step}] ${message}`);
    this.name = 'PipelineStepError';
  }
}

export function isRetryableError(error: unknown): boolean {
  if (error instanceof PipelineStepError) {
    return error.retryable;
  }
  
  // Network errors are retryable
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return true;
  }
  
  // Rate limits are retryable
  if (error instanceof Error && error.message.includes('rate limit')) {
    return true;
  }
  
  return false;
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 3,
  delayMs: number = 1000
): Promise<T> {
  let lastError: unknown;
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      if (!isRetryableError(error) || attempt === maxAttempts) {
        throw error;
      }
      
      await new Promise(r => setTimeout(r, delayMs * attempt));
    }
  }
  
  throw lastError;
}
```

### Step 5: Wire Up API Endpoint

**File**: `api/routes/tryon.routes.ts`

**Purpose**: Expose pipeline via HTTP with SSE progress updates

**Pattern**:
```typescript
import { Router } from 'express';
import { runTryOnPipeline } from '../services/pipeline/orchestrator';

const router = Router();

router.post('/generate', async (req, res) => {
  const { userImageUrl, garmentImageUrl } = req.body;
  
  if (!userImageUrl || !garmentImageUrl) {
    return res.status(400).json({ error: 'Missing required image URLs' });
  }

  // Set up SSE for progress
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  
  const sendProgress = (step: string, progress: number) => {
    res.write(`data: ${JSON.stringify({ type: 'progress', step, progress })}\n\n`);
  };

  try {
    const result = await runTryOnPipeline(
      userImageUrl,
      garmentImageUrl,
      sendProgress
    );
    
    res.write(`data: ${JSON.stringify({ type: 'complete', result })}\n\n`);
    res.end();
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Pipeline failed';
    res.write(`data: ${JSON.stringify({ type: 'error', message })}\n\n`);
    res.end();
  }
});

export default router;
```

### Step 6: Environment Variables

**File**: `.env.example`

**Purpose**: Document required API keys

```bash
# Remove.bg - Background removal
REMOVEBG_API_KEY=your_key_here

# Anthropic - Garment detection
ANTHROPIC_API_KEY=your_key_here

# Replicate - IDM-VTON, ESRGAN, CodeFormer
REPLICATE_API_TOKEN=your_token_here
```

---

## Verification

### Unit Test Each Step

```bash
# Test garment extraction
curl -X POST http://localhost:3000/api/test/extract \
  -H "Content-Type: application/json" \
  -d '{"imageUrl": "https://example.com/shirt.jpg"}'
```

### Integration Test Full Pipeline

```bash
# Full pipeline test with SSE
curl -N -X POST http://localhost:3000/api/tryon/generate \
  -H "Content-Type: application/json" \
  -d '{
    "userImageUrl": "https://example.com/person.jpg",
    "garmentImageUrl": "https://example.com/shirt.jpg"
  }'
```

**Expected Result**:
```
data: {"type":"progress","step":"extract","progress":0}
data: {"type":"progress","step":"detect","progress":15}
data: {"type":"progress","step":"generate","progress":25}
data: {"type":"progress","step":"upscale","progress":70}
data: {"type":"progress","step":"enhance","progress":85}
data: {"type":"progress","step":"complete","progress":100}
data: {"type":"complete","result":{"finalImageUrl":"https://...",...}}
```

### Timing Baseline

| Step | Expected Duration |
|------|-------------------|
| Extract (Remove.bg) | 2-5s |
| Detect (Claude) | 1-2s |
| Generate (IDM-VTON) | 45-60s |
| Upscale (ESRGAN) | 5-10s |
| Enhance (CodeFormer) | 5-10s |
| **Total** | **~65s** |

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 2 complete
2. Proceed to Task 3 (Database schema) or Task 4 (Frontend upload)—both can now start

---

## Related Documents

- [Architecture](./architecture.md) — Why pipeline orchestration over monolithic AI
- [Epic](./epic.md) — Task dependencies and MVP scope
- [Timeline](./timeline.md) — Status tracking