# 🛠️ Task 4: Catalog Garments

**Purpose**: Curate and prepare 10 initial garments with pre-processed masks to enable faster try-on requests for catalog items.

**Effort**: 0.5 days

**Dependencies**: Task 2 (Garment extraction pipeline) must be complete

**Parallel With**: Task 5 (Face enhancement integration)

**Blocks**: Task 6 (MVP launch) – catalog items are required for launch

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Selecting 10 high-quality garment images across categories
- Running garment extraction pipeline on each
- Storing pre-processed masks alongside originals
- Creating catalog metadata structure

### What's NOT Included
- User-uploaded garment processing — handled by real-time pipeline
- Garment categorization ML — manual tagging for MVP
- E-commerce integration — future feature

---

## Prerequisites

Before starting:
- Garment extraction pipeline (Task 2) working and tested
- Access to Remove.bg API or equivalent for mask generation
- Storage bucket configured for catalog assets
- 10 garment source images selected (see Selection Criteria below)

---

## Selection Criteria

Choose garments that showcase the try-on pipeline well:

| Category | Count | Criteria |
|----------|-------|----------|
| Tops | 4 | Mix of fitted/loose, solid/pattern |
| Dresses | 3 | Varied necklines and lengths |
| Jackets | 3 | Blazer, casual, outerwear variety |

**Image Requirements**:
- Resolution: minimum 1024x1024
- Background: plain or easily removable
- Garment: flat-lay or mannequin (no human models)
- Lighting: even, minimal shadows

---

## Implementation Steps

### Step 1: Create Catalog Directory Structure

**File**: `catalog/` (new directory)

**Purpose**: Organize catalog assets for consistent access

```
catalog/
├── tops/
│   ├── top-001/
│   │   ├── original.jpg
│   │   ├── mask.png
│   │   └── metadata.json
│   └── top-002/
│       └── ...
├── dresses/
│   └── dress-001/
│       └── ...
└── jackets/
    └── jacket-001/
        └── ...
```

### Step 2: Define Metadata Schema

**File**: `catalog/schema.json`

**Purpose**: Consistent metadata structure for all catalog items

```json
{
  "id": "top-001",
  "category": "tops",
  "name": "White Cotton Blouse",
  "tags": ["casual", "summer", "solid"],
  "originalPath": "catalog/tops/top-001/original.jpg",
  "maskPath": "catalog/tops/top-001/mask.png",
  "dimensions": { "width": 1024, "height": 1024 },
  "processedAt": "2026-04-05T12:00:00Z"
}
```

### Step 3: Create Batch Processing Script

**File**: `scripts/process-catalog.js` (or `.py`)

**Purpose**: Automate mask generation for all catalog garments

```javascript
// Pattern: iterate catalog, extract masks, save alongside originals
async function processCatalog(catalogDir) {
  const categories = ['tops', 'dresses', 'jackets'];
  
  for (const category of categories) {
    const items = await getItemsInCategory(catalogDir, category);
    
    for (const item of items) {
      // Skip if mask already exists
      if (await maskExists(item)) continue;
      
      // Run extraction pipeline (from Task 2)
      const mask = await extractGarmentMask(item.originalPath);
      
      // Save mask alongside original
      await saveMask(mask, item.maskPath);
      
      // Update metadata
      await updateMetadata(item, { processedAt: new Date() });
    }
  }
}
```

### Step 4: Process Each Garment

**Purpose**: Generate masks for all 10 garments

Run the extraction pipeline on each garment:

```bash
# Process entire catalog
node scripts/process-catalog.js

# Or process individual item for testing
node scripts/process-catalog.js --item tops/top-001
```

**Quality Check**: After each extraction, verify:
- Mask cleanly isolates garment (no background bleed)
- Edges are crisp, not jagged
- Transparent regions are fully transparent (alpha = 0)

### Step 5: Create Catalog Index

**File**: `catalog/index.json`

**Purpose**: Single source of truth for available catalog items

```json
{
  "version": "1.0",
  "lastUpdated": "2026-04-05T12:00:00Z",
  "items": [
    {
      "id": "top-001",
      "category": "tops",
      "name": "White Cotton Blouse",
      "thumbnail": "/catalog/tops/top-001/original.jpg"
    }
    // ... remaining 9 items
  ]
}
```

### Step 6: Add Catalog Endpoint

**File**: `api/routes/catalog.js`

**Purpose**: Serve catalog items to frontend

```javascript
// GET /api/catalog - list all items
router.get('/catalog', async (req, res) => {
  const index = await readJSON('catalog/index.json');
  res.json(index.items);
});

// GET /api/catalog/:id - get specific item with paths
router.get('/catalog/:id', async (req, res) => {
  const metadata = await readJSON(`catalog/**/${req.params.id}/metadata.json`);
  res.json(metadata);
});
```

---

## Verification

### 1. Catalog Structure Check

```bash
# Verify all items have required files
find catalog -name "metadata.json" | wc -l
# Expected: 10

find catalog -name "mask.png" | wc -l
# Expected: 10
```

### 2. API Endpoint Check

```bash
# List catalog
curl http://localhost:3100/api/catalog
# Expected: JSON array with 10 items

# Get specific item
curl http://localhost:3100/api/catalog/top-001
# Expected: Full metadata including mask path
```

### 3. Visual Verification

For each of the 10 items:
1. Open original image
2. Open mask as overlay
3. Confirm mask accurately covers garment only

**Expected Result**: 10 catalog items with clean masks, accessible via API, ready for try-on requests.

---

## Performance Benefit

With pre-processed masks, catalog try-on requests skip the extraction step:

| Flow | Without Pre-processing | With Pre-processing |
|------|------------------------|---------------------|
| User photo → mask | ~5s | ~5s |
| Garment → mask | ~5s | **0s (cached)** |
| Try-on generation | ~45s | ~45s |
| **Total** | ~55s | **~50s** |

The 5-second savings compounds with every try-on request using catalog items.

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 4 complete
2. Proceed to Task 5 (Face enhancement integration)
3. Use catalog items for end-to-end pipeline testing

---

## Related Documents

- [Architecture](./architecture.md) – Pipeline modularity design
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking