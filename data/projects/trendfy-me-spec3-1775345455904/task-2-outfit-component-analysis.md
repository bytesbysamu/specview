# 🛠️ Task 2: Outfit Component Analysis

**Purpose**: Build an AI-powered analysis service that breaks down outfit images into structured, searchable metadata using Claude's vision capabilities.

**Effort**: 2 days

**Dependencies**: Task 1 (Content ingestion pipeline) must be complete—we need images to analyze.

**Parallel With**: Task 3 (Trend signal extraction) can begin once the output schema is finalized.

**Blocks**: Task 3 (trend extraction), Task 4 (trend scoring)—both depend on component metadata.

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Claude vision API integration for outfit analysis
- Structured output schema for garment metadata
- Batch processing pipeline for queued images
- Metadata storage and indexing

### What's NOT Included
- Custom ML model training — Claude handles classification
- Real-time analysis — batch processing only per architecture
- Brand/logo recognition — legal complexity, defer to later phase
- Price estimation — requires external data sources

---

## Prerequisites

Before starting:
- Claude API key with vision capabilities enabled
- Task 1 complete: images stored with URLs accessible to the API
- Database schema for `outfit_components` table
- Familiarity with Claude's vision API response format

---

## Implementation Steps

### Step 1: Define Component Schema

**File**: `src/schemas/outfit-components.ts`

**Purpose**: Establish the structured output format that all downstream services expect.

The schema must be specific enough for trend analysis but flexible enough to handle fashion's inherent ambiguity. A single garment can belong to multiple categories (a "blazer dress" is both outerwear and dress).

**Pattern**:
```typescript
interface OutfitComponent {
  id: string;
  imageId: string;
  garments: Garment[];
  overallStyle: StyleTag[];
  occasions: OccasionTag[];
  confidence: number;
  analyzedAt: Date;
}

interface Garment {
  type: GarmentType;        // 'top' | 'bottom' | 'dress' | 'outerwear' | 'footwear' | 'accessory'
  subtype: string;          // 'blazer', 'midi-skirt', 'sneakers', etc.
  primaryColor: ColorInfo;
  secondaryColors: ColorInfo[];
  pattern: PatternType;     // 'solid' | 'striped' | 'plaid' | 'floral' | 'animal' | 'geometric' | 'other'
  material?: string;        // 'denim', 'leather', 'knit', 'silk' — optional, lower confidence
  fit: FitType;             // 'oversized' | 'fitted' | 'relaxed' | 'tailored'
}

interface ColorInfo {
  name: string;             // 'burgundy', 'cream', 'forest green'
  hex: string;              // '#8B0000' — for visual display
  family: ColorFamily;      // 'red' | 'blue' | 'neutral' | etc. — for aggregation
}

type StyleTag = 'minimalist' | 'streetwear' | 'bohemian' | 'preppy' | 'athleisure' | 
                'romantic' | 'edgy' | 'classic' | 'maximalist' | 'coastal';

type OccasionTag = 'casual' | 'work' | 'formal' | 'date-night' | 'weekend' | 
                   'vacation' | 'workout' | 'evening';
```

### Step 2: Create Vision Analysis Prompt

**File**: `src/services/outfit-analyzer.ts`

**Purpose**: Craft the prompt that extracts consistent, structured data from outfit images.

The prompt must guide Claude to output JSON that matches our schema. Include examples of edge cases (layered outfits, partial views, multiple people in frame).

**Pattern**:
```typescript
const ANALYSIS_PROMPT = `Analyze this outfit image and extract structured fashion metadata.

Output JSON matching this exact structure:
{
  "garments": [
    {
      "type": "top|bottom|dress|outerwear|footwear|accessory",
      "subtype": "specific garment name",
      "primaryColor": { "name": "color name", "hex": "#XXXXXX", "family": "color family" },
      "secondaryColors": [],
      "pattern": "solid|striped|plaid|floral|animal|geometric|other",
      "material": "if clearly identifiable, else null",
      "fit": "oversized|fitted|relaxed|tailored"
    }
  ],
  "overallStyle": ["up to 3 style tags"],
  "occasions": ["up to 3 occasion tags"],
  "confidence": 0.0-1.0
}

Rules:
- List garments from top to bottom (hat → top → bottom → shoes)
- If multiple outfits visible, analyze only the primary/centered person
- For layered pieces, list each visible layer separately
- Confidence reflects image quality and visibility (low for blurry/partial views)
- Use lowercase for all string values
- Hex colors should be approximate—prioritize the named color being accurate`;

async function analyzeOutfit(imageUrl: string): Promise<OutfitComponent> {
  const response = await claude.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 1024,
    messages: [{
      role: 'user',
      content: [
        { type: 'image', source: { type: 'url', url: imageUrl } },
        { type: 'text', text: ANALYSIS_PROMPT }
      ]
    }]
  });
  
  // Parse and validate response
  const parsed = JSON.parse(response.content[0].text);
  return validateAndTransform(parsed);
}
```

### Step 3: Implement Batch Processing Queue

**File**: `src/workers/analysis-worker.ts`

**Purpose**: Process ingested images in batches, respecting API rate limits and handling failures gracefully.

Per architecture's "degrade gracefully" principle, failed analyses should be retried with backoff, not block the pipeline.

**Pattern**:
```typescript
interface AnalysisJob {
  imageId: string;
  imageUrl: string;
  attempts: number;
  lastError?: string;
}

class AnalysisWorker {
  private readonly BATCH_SIZE = 10;
  private readonly MAX_RETRIES = 3;
  private readonly RATE_LIMIT_DELAY = 200; // ms between API calls

  async processBatch(): Promise<void> {
    const pendingImages = await db.images.findMany({
      where: { analysisStatus: 'pending' },
      take: this.BATCH_SIZE
    });

    for (const image of pendingImages) {
      try {
        await this.markInProgress(image.id);
        
        const components = await analyzeOutfit(image.url);
        await this.saveComponents(image.id, components);
        await this.markComplete(image.id);
        
        await sleep(this.RATE_LIMIT_DELAY);
      } catch (error) {
        await this.handleFailure(image.id, error);
      }
    }
  }

  private async handleFailure(imageId: string, error: Error): Promise<void> {
    const attempts = await this.incrementAttempts(imageId);
    
    if (attempts >= this.MAX_RETRIES) {
      await this.markFailed(imageId, error.message);
      // Don't block pipeline—log and continue
      console.error(`Analysis failed permanently for ${imageId}:`, error);
    } else {
      // Reset to pending for retry with exponential backoff
      await this.markPendingWithDelay(imageId, attempts * 60_000);
    }
  }
}
```

### Step 4: Store and Index Components

**File**: `src/db/migrations/002_outfit_components.sql`

**Purpose**: Create storage that supports efficient querying for trend analysis (aggregating by color, style, garment type).

**Pattern**:
```sql
CREATE TABLE outfit_components (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  image_id UUID NOT NULL REFERENCES images(id),
  overall_style TEXT[] NOT NULL,
  occasions TEXT[] NOT NULL,
  confidence DECIMAL(3,2) NOT NULL,
  analyzed_at TIMESTAMP NOT NULL DEFAULT NOW(),
  raw_response JSONB NOT NULL  -- Store full response for debugging/reprocessing
);

CREATE TABLE garments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  component_id UUID NOT NULL REFERENCES outfit_components(id) ON DELETE CASCADE,
  type VARCHAR(20) NOT NULL,
  subtype VARCHAR(50) NOT NULL,
  primary_color_name VARCHAR(50) NOT NULL,
  primary_color_hex CHAR(7) NOT NULL,
  primary_color_family VARCHAR(20) NOT NULL,
  pattern VARCHAR(20) NOT NULL,
  material VARCHAR(50),
  fit VARCHAR(20) NOT NULL
);

-- Indexes for trend aggregation queries
CREATE INDEX idx_garments_type ON garments(type);
CREATE INDEX idx_garments_color_family ON garments(primary_color_family);
CREATE INDEX idx_garments_pattern ON garments(pattern);
CREATE INDEX idx_components_style ON outfit_components USING GIN(overall_style);
CREATE INDEX idx_components_analyzed ON outfit_components(analyzed_at);
```

### Step 5: Add Analysis Status Tracking

**File**: `src/services/analysis-status.ts`

**Purpose**: Track pipeline health and surface issues before they compound.

**Pattern**:
```typescript
interface AnalysisStats {
  pending: number;
  inProgress: number;
  completed: number;
  failed: number;
  avgConfidence: number;
  lastProcessedAt: Date | null;
}

async function getAnalysisStats(): Promise<AnalysisStats> {
  const [counts, avgConf, lastProcessed] = await Promise.all([
    db.$queryRaw`
      SELECT analysis_status, COUNT(*) 
      FROM images 
      GROUP BY analysis_status
    `,
    db.outfitComponents.aggregate({ _avg: { confidence: true } }),
    db.outfitComponents.findFirst({ orderBy: { analyzedAt: 'desc' } })
  ]);
  
  return {
    pending: counts.find(c => c.status === 'pending')?.count ?? 0,
    inProgress: counts.find(c => c.status === 'in_progress')?.count ?? 0,
    completed: counts.find(c => c.status === 'complete')?.count ?? 0,
    failed: counts.find(c => c.status === 'failed')?.count ?? 0,
    avgConfidence: avgConf._avg.confidence ?? 0,
    lastProcessedAt: lastProcessed?.analyzedAt ?? null
  };
}
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Run a single image through analysis
npm run script -- analyze-single --url "https://example.com/outfit.jpg"

# 2. Check the output structure
psql -c "SELECT * FROM outfit_components ORDER BY analyzed_at DESC LIMIT 1;"
psql -c "SELECT * FROM garments WHERE component_id = '<id from above>';"

# 3. Run batch processing on test set
npm run worker:analysis -- --batch-size 5

# 4. Verify aggregation queries work
psql -c "SELECT primary_color_family, COUNT(*) FROM garments GROUP BY primary_color_family;"
```

**Expected Result**:
- Single image returns valid JSON matching schema
- Garments table populated with 2-6 entries per outfit
- Confidence scores between 0.7-0.95 for clear images
- Aggregation queries return meaningful distributions

---

## Edge Cases to Test

| Case | Expected Behavior |
|------|-------------------|
| Blurry image | Lower confidence score (< 0.6), still attempt analysis |
| Multiple people | Analyze center/primary person only |
| Close-up (single garment) | Return single garment, appropriate occasions |
| Non-fashion image | Very low confidence, minimal garments array |
| API timeout | Retry with backoff, mark failed after 3 attempts |

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 2 complete
2. Proceed to Task 3: Trend signal extraction (uses component metadata)
3. Schedule batch analysis to run after ingestion pipeline (cron or queue trigger)

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale, "pre-compute over real-time" principle
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking