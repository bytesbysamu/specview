# 🛠️ Task 4: Wardrobe Photo Matching

**Purpose**: Enable users to upload photos of their clothing items and receive AI-powered matches against trending outfits, starting with single-item matching before expanding to full outfit assembly.

**Effort**: 2 days

**Dependencies**: Task 1 (Core Platform + Trend Feed) must be complete for trend data access

**Parallel With**: Task 5 (Fashion Calendar), Task 6 (Style Profile Quiz)

**Blocks**: Future outfit assembly features, personalized trend recommendations

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Photo upload interface with drag-drop and camera capture
- AI-powered clothing item detection and classification
- Single-item matching against trending outfits
- Match results UI with confidence scores and trend context
- Basic image optimization and storage

### What's NOT Included
- Full outfit assembly from multiple items — phase 2 feature
- Virtual try-on or AR overlays — requires significant additional infrastructure
- Brand/retailer identification — privacy and accuracy concerns
- User wardrobe persistence — focus on single-session matching first

---

## Prerequisites

Before starting:
- Trend data pipeline operational (Task 1)
- Vision AI service configured (Claude or dedicated vision model)
- Image storage solution ready (S3/Cloudflare R2)
- Understanding of fashion attribute taxonomy (color, style, category)

---

## Implementation Steps

### Step 1: Image Upload Component

**File**: `src/components/wardrobe/PhotoUpload.tsx`

**Purpose**: Create a user-friendly upload interface that handles both file selection and camera capture on mobile.

The upload component needs to handle multiple input methods while providing immediate visual feedback. Compress images client-side before upload to reduce latency and storage costs.

**Pattern**:
```typescript
// Core upload handler with client-side optimization
const processUpload = async (file: File) => {
  // Validate file type and size
  if (!ALLOWED_TYPES.includes(file.type)) {
    throw new Error('Please upload a JPG, PNG, or WebP image');
  }
  
  // Compress to max 1200px width, 80% quality
  const optimized = await compressImage(file, {
    maxWidth: 1200,
    quality: 0.8
  });
  
  // Generate preview immediately
  setPreview(URL.createObjectURL(optimized));
  
  return optimized;
};
```

**UI considerations**:
- Large drop zone with clear visual affordance
- Mobile: prominent camera button alongside file picker
- Show upload progress and processing states
- Allow retry on failure without full page reload

### Step 2: Clothing Detection Service

**File**: `src/services/clothing-detection.ts`

**Purpose**: Extract clothing attributes from uploaded photos using vision AI.

This service wraps the vision model call and normalizes responses into a structured format. The prompt engineering here is critical—be specific about what attributes to extract.

**Pattern**:
```typescript
interface ClothingAttributes {
  category: 'top' | 'bottom' | 'dress' | 'outerwear' | 'shoes' | 'accessory';
  style: string[];      // e.g., ['casual', 'minimalist']
  colors: string[];     // primary and accent colors
  patterns: string[];   // solid, striped, floral, etc.
  occasion: string[];   // work, casual, formal, athletic
  confidence: number;   // 0-1 detection confidence
}

const detectClothing = async (imageUrl: string): Promise<ClothingAttributes> => {
  const response = await visionModel.analyze({
    image: imageUrl,
    prompt: `Analyze this clothing item. Extract:
    - Category (top/bottom/dress/outerwear/shoes/accessory)
    - Style descriptors (max 3)
    - Primary and accent colors
    - Pattern type
    - Suitable occasions
    
    Return JSON only. If multiple items visible, focus on the most prominent.`
  });
  
  return parseClothingResponse(response);
};
```

**Error handling**:
- No clothing detected → prompt user to retake photo
- Multiple items → return primary item with note
- Low confidence → still return results but flag for user

### Step 3: Trend Matching Algorithm

**File**: `src/services/trend-matcher.ts`

**Purpose**: Match detected clothing attributes against trending outfits in the database.

Matching uses weighted attribute comparison. Color and category are hard filters; style and occasion contribute to relevance scoring.

**Pattern**:
```typescript
interface MatchResult {
  trend: TrendItem;
  score: number;           // 0-100 relevance score
  matchReasons: string[];  // why this matches
}

const findMatches = async (
  attributes: ClothingAttributes,
  limit: number = 5
): Promise<MatchResult[]> => {
  // Query trends that include this category
  const candidates = await db.trends
    .where('clothing_categories', 'contains', attributes.category)
    .where('momentum_score', '>', 0.3)  // only active trends
    .orderBy('momentum_score', 'desc')
    .limit(50);
  
  // Score each candidate
  const scored = candidates.map(trend => ({
    trend,
    score: calculateMatchScore(attributes, trend),
    matchReasons: explainMatch(attributes, trend)
  }));
  
  // Return top matches above threshold
  return scored
    .filter(m => m.score > 40)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
};

const calculateMatchScore = (attrs: ClothingAttributes, trend: TrendItem): number => {
  let score = 0;
  
  // Color harmony (0-30 points)
  score += scoreColorMatch(attrs.colors, trend.colorPalette) * 30;
  
  // Style alignment (0-40 points)
  score += scoreStyleMatch(attrs.style, trend.styleAttributes) * 40;
  
  // Occasion fit (0-20 points)
  score += scoreOccasionMatch(attrs.occasion, trend.occasions) * 20;
  
  // Recency boost (0-10 points)
  score += trend.momentum_score * 10;
  
  return Math.round(score);
};
```

### Step 4: Match Results UI

**File**: `src/components/wardrobe/MatchResults.tsx`

**Purpose**: Display matching trends in a scannable, actionable format.

Users need to quickly understand why each trend matches and how to style their item. Prioritize visual examples over text descriptions.

**Pattern**:
```tsx
const MatchResults = ({ userImage, matches }: Props) => {
  return (
    <div className="match-results">
      {/* User's uploaded item for reference */}
      <div className="user-item">
        <img src={userImage} alt="Your item" />
        <p className="detected-label">{detectedCategory}</p>
      </div>
      
      {/* Matching trends */}
      <div className="matches-grid">
        {matches.map(match => (
          <MatchCard key={match.trend.id}>
            <TrendImage src={match.trend.imageUrl} />
            <MatchScore score={match.score} />
            <MatchReasons reasons={match.matchReasons} />
            <ViewTrendLink trend={match.trend} />
          </MatchCard>
        ))}
      </div>
      
      {/* No matches state */}
      {matches.length === 0 && (
        <EmptyState 
          message="No trending matches found"
          suggestion="Try a different item or check back as trends update"
        />
      )}
    </div>
  );
};
```

**Key UI elements**:
- Side-by-side comparison: user item ↔ trend example
- Match score as visual indicator (not just number)
- 2-3 word reason tags ("color match", "similar vibe")
- Clear CTA to explore full trend

### Step 5: API Endpoint

**File**: `src/api/wardrobe/match.ts`

**Purpose**: Orchestrate the upload → detect → match flow with proper error handling and rate limiting.

**Pattern**:
```typescript
// POST /api/wardrobe/match
export const matchWardrobe = async (req: Request, res: Response) => {
  const { image } = req.body;  // base64 or URL
  
  try {
    // 1. Store image and get URL
    const imageUrl = await storage.upload(image, {
      folder: 'wardrobe-uploads',
      expires: '24h'  // temporary storage
    });
    
    // 2. Detect clothing attributes
    const attributes = await detectClothing(imageUrl);
    
    if (attributes.confidence < 0.3) {
      return res.status(400).json({
        error: 'Could not identify clothing item',
        suggestion: 'Try a clearer photo with the item as the main focus'
      });
    }
    
    // 3. Find matches
    const matches = await findMatches(attributes, 5);
    
    // 4. Return results
    return res.json({
      detected: attributes,
      matches,
      imageUrl  // for display in results
    });
    
  } catch (error) {
    logger.error('Wardrobe match failed', { error });
    return res.status(500).json({
      error: 'Matching failed',
      suggestion: 'Please try again'
    });
  }
};
```

### Step 6: Performance Optimization

**File**: Various

**Purpose**: Ensure the matching flow completes in under 3 seconds for good UX.

**Optimizations**:

```typescript
// 1. Parallel processing where possible
const [imageUrl, cachedTrends] = await Promise.all([
  storage.upload(image),
  cache.get('active-trends')  // pre-fetch trend data
]);

// 2. Image preprocessing hints
// Tell vision model to focus on clothing, skip background analysis
const detectionPrompt = `
Focus only on clothing items. Ignore:
- Background elements
- People's faces
- Brand logos
Return attributes for the primary garment only.
`;

// 3. Result caching
// Cache trend data aggressively (refreshed by Task 1 pipeline)
const getCandidateTrends = cache.wrap(
  'candidate-trends',
  () => db.trends.where('momentum_score', '>', 0.3).get(),
  { ttl: 300 }  // 5 minutes
);
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Test upload flow
curl -X POST http://localhost:3100/api/wardrobe/match \
  -H "Content-Type: application/json" \
  -d '{"image": "data:image/jpeg;base64,..."}'

# 2. Verify detection accuracy
# Upload 10 test images across categories, check detection results

# 3. Load test matching endpoint
ab -n 100 -c 10 http://localhost:3100/api/wardrobe/match
```

**Expected Results**:
- Upload completes in < 500ms
- Detection returns valid attributes for clear clothing photos
- Matching returns 0-5 results in < 2 seconds
- No matches for non-clothing images (graceful handling)

**Manual verification**:
1. Upload a white button-down shirt → should match business/minimalist trends
2. Upload a floral dress → should match spring/romantic trends
3. Upload a photo of a coffee cup → should return "no clothing detected" error

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 4 complete
2. Gather early user feedback on match quality
3. Consider Task 5 (Fashion Calendar) or Task 6 (Style Quiz) based on priorities
4. Document common detection failures for prompt improvement

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale and AI pipeline structure
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking