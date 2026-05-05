# 🛠️ Task 1: Trend Scraping Infrastructure

**Purpose**: Build the foundation for collecting fashion trend data from social platforms, storing images and metadata in a structured format for downstream AI analysis.

**Effort**: 2 days

**Dependencies**: None — this is the first task

**Parallel With**: —

**Blocks**: Task 2 (Trend Detection AI), Task 3 (Frontend)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Pinterest RSS/API scraper for fashion boards
- Instagram public feed scraper (hashtag-based)
- Image storage with metadata schema
- Scheduling system for automated collection
- Deduplication logic

### What's NOT Included
- AI analysis — handled in Task 2
- User authentication — not needed for scraping
- Rate limit sophistication — start simple, iterate if blocked

---

## Prerequisites

Before starting:
- Node.js 20+ or Python 3.11+ (choose one stack)
- PostgreSQL or SQLite for metadata storage
- S3-compatible storage for images (or local filesystem for MVP)
- Understanding of rate limiting and robots.txt compliance

---

## Implementation Steps

### Step 1: Define the Data Schema

**File**: `services/scraper/schema.sql` or equivalent ORM

**Purpose**: Establish consistent structure for trend images before writing any scraping code

The schema prioritizes **metadata richness** over image storage. Each record captures provenance (where it came from), engagement signals (likes, saves, comments), and processing state.

**Pattern**:
```sql
CREATE TABLE trend_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_platform VARCHAR(50) NOT NULL,  -- 'pinterest', 'instagram'
  source_url TEXT NOT NULL UNIQUE,        -- deduplication key
  image_url TEXT NOT NULL,
  local_path TEXT,                        -- after download
  
  -- Engagement metrics (nullable—not all platforms expose all)
  likes_count INTEGER,
  saves_count INTEGER,
  comments_count INTEGER,
  
  -- Content metadata
  caption TEXT,
  hashtags TEXT[],
  author_handle VARCHAR(255),
  
  -- Processing state
  scraped_at TIMESTAMP DEFAULT NOW(),
  analyzed_at TIMESTAMP,                  -- set by Task 2
  trend_score FLOAT,                      -- set by Task 2
  
  -- Quality flags
  is_duplicate BOOLEAN DEFAULT FALSE,
  is_relevant BOOLEAN                     -- fashion vs noise
);

CREATE INDEX idx_source_url ON trend_images(source_url);
CREATE INDEX idx_scraped_at ON trend_images(scraped_at);
```

### Step 2: Build the Pinterest Scraper

**File**: `services/scraper/platforms/pinterest.ts`

**Purpose**: Extract fashion content from Pinterest's public feeds

Pinterest offers RSS feeds for boards and some search results. This is more reliable than HTML scraping and less likely to trigger blocks.

**Pattern**:
```typescript
interface ScrapedImage {
  sourceUrl: string;
  imageUrl: string;
  caption?: string;
  platform: 'pinterest';
  scrapedAt: Date;
}

async function scrapePinterestBoard(boardUrl: string): Promise<ScrapedImage[]> {
  // Pinterest RSS endpoint pattern
  const rssUrl = `${boardUrl}.rss`;
  
  const response = await fetch(rssUrl);
  const xml = await response.text();
  
  // Parse RSS, extract items
  const items = parseRss(xml);
  
  return items.map(item => ({
    sourceUrl: item.link,
    imageUrl: extractImageFromDescription(item.description),
    caption: item.title,
    platform: 'pinterest',
    scrapedAt: new Date()
  }));
}

// Target boards for fashion trends
const FASHION_BOARDS = [
  'https://pinterest.com/pinterest/fashion-trends',
  'https://pinterest.com/whowhatwear/street-style',
  // Add 5-10 curated boards
];
```

### Step 3: Build the Instagram Scraper

**File**: `services/scraper/platforms/instagram.ts`

**Purpose**: Collect public Instagram posts by hashtag

Instagram's official API requires business accounts. For MVP, use a lightweight approach targeting public hashtag pages. Be conservative with request rates.

**Pattern**:
```typescript
async function scrapeInstagramHashtag(hashtag: string): Promise<ScrapedImage[]> {
  // Use a headless browser or proxy service for reliability
  // Instagram blocks naive fetch requests
  
  const posts = await fetchHashtagPosts(hashtag, { limit: 20 });
  
  return posts
    .filter(post => post.mediaType === 'image') // skip videos for now
    .map(post => ({
      sourceUrl: `https://instagram.com/p/${post.shortcode}`,
      imageUrl: post.displayUrl,
      caption: post.caption,
      likesCount: post.likesCount,
      authorHandle: post.ownerUsername,
      hashtags: extractHashtags(post.caption),
      platform: 'instagram',
      scrapedAt: new Date()
    }));
}

const FASHION_HASHTAGS = [
  'streetstyle',
  'ootd',
  'fashiontrends2026',
  // 10-15 targeted hashtags
];
```

### Step 4: Image Download and Storage

**File**: `services/scraper/storage.ts`

**Purpose**: Download images locally and track storage paths

Downloading images ensures you're not dependent on source URLs staying valid. Store originals; let the AI pipeline handle resizing.

**Pattern**:
```typescript
async function downloadAndStore(image: ScrapedImage): Promise<string> {
  const response = await fetch(image.imageUrl);
  const buffer = await response.arrayBuffer();
  
  // Generate deterministic filename from source URL
  const hash = crypto.createHash('md5').update(image.sourceUrl).digest('hex');
  const ext = detectImageFormat(buffer); // jpg, png, webp
  const filename = `${hash}.${ext}`;
  
  const localPath = path.join(STORAGE_DIR, filename);
  await fs.writeFile(localPath, Buffer.from(buffer));
  
  return localPath;
}

// For S3 deployment, swap to:
async function uploadToS3(buffer: Buffer, key: string): Promise<string> {
  // Return S3 URL instead of local path
}
```

### Step 5: Deduplication Logic

**File**: `services/scraper/dedup.ts`

**Purpose**: Prevent storing the same image twice across runs

Source URL is the primary dedup key. For cross-platform duplicates (same image on Pinterest and Instagram), add perceptual hashing later.

**Pattern**:
```typescript
async function isDuplicate(sourceUrl: string): Promise<boolean> {
  const existing = await db.query(
    'SELECT id FROM trend_images WHERE source_url = $1',
    [sourceUrl]
  );
  return existing.rows.length > 0;
}

async function saveIfNew(image: ScrapedImage): Promise<boolean> {
  if (await isDuplicate(image.sourceUrl)) {
    return false; // already have it
  }
  
  const localPath = await downloadAndStore(image);
  
  await db.query(`
    INSERT INTO trend_images 
    (source_platform, source_url, image_url, local_path, caption, hashtags, likes_count, author_handle)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
  `, [
    image.platform,
    image.sourceUrl,
    image.imageUrl,
    localPath,
    image.caption,
    image.hashtags,
    image.likesCount,
    image.authorHandle
  ]);
  
  return true;
}
```

### Step 6: Scheduler and Orchestration

**File**: `services/scraper/scheduler.ts`

**Purpose**: Run scraping jobs on a schedule without manual intervention

Per the architecture's "pre-compute over real-time" principle, scraping runs on a fixed schedule. Start with twice daily; adjust based on rate limits and data freshness needs.

**Pattern**:
```typescript
import cron from 'node-cron';

async function runScrapingJob() {
  console.log(`[${new Date().toISOString()}] Starting scraping job`);
  
  let newImages = 0;
  
  // Pinterest
  for (const board of FASHION_BOARDS) {
    try {
      const images = await scrapePinterestBoard(board);
      for (const img of images) {
        if (await saveIfNew(img)) newImages++;
      }
    } catch (err) {
      console.error(`Pinterest scrape failed for ${board}:`, err.message);
      // Continue with other sources — graceful degradation
    }
  }
  
  // Instagram
  for (const hashtag of FASHION_HASHTAGS) {
    try {
      const images = await scrapeInstagramHashtag(hashtag);
      for (const img of images) {
        if (await saveIfNew(img)) newImages++;
      }
      // Rate limit between hashtags
      await sleep(5000);
    } catch (err) {
      console.error(`Instagram scrape failed for #${hashtag}:`, err.message);
    }
  }
  
  console.log(`[${new Date().toISOString()}] Scraping complete. ${newImages} new images.`);
}

// Run at 6am and 6pm
cron.schedule('0 6,18 * * *', runScrapingJob);

// Also expose manual trigger for testing
export { runScrapingJob };
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Initialize database
psql -f services/scraper/schema.sql

# 2. Run scraper manually
npm run scrape:manual
# or
node -e "require('./services/scraper/scheduler').runScrapingJob()"

# 3. Check results
psql -c "SELECT COUNT(*) FROM trend_images;"
# Expected: 30-100 rows after first run

psql -c "SELECT source_platform, COUNT(*) FROM trend_images GROUP BY source_platform;"
# Expected: Mix of pinterest and instagram

# 4. Verify images downloaded
ls -la ./storage/images/ | head -20
# Expected: .jpg/.png files with hash-based names
```

**Expected Result**: 
- 50+ new images per day across platforms
- No duplicate source URLs in database
- Images accessible locally for AI analysis
- Scheduler running without manual intervention

---

## Gotchas and Edge Cases

| Issue | Mitigation |
|-------|------------|
| Instagram blocks requests | Use rotating proxies or a service like Apify |
| Pinterest RSS missing images | Fall back to HTML scraping for those boards |
| Storage fills up | Add cleanup job for images older than 30 days |
| Duplicate images across platforms | Phase 2: add perceptual hashing |

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 1 as done
2. Proceed to Task 2 (Trend Detection AI) — it consumes the `trend_images` table

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for pipeline approach
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking