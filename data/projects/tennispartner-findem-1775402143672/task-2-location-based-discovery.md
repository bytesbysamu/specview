# 🛠️ Task 2: Location-Based Discovery

**Purpose**: Enable players to find tennis partners nearby using geospatial search, sorted by distance and compatibility score.

**Effort**: 4 days

**Dependencies**: Task 1 (User profiles with location data stored)

**Parallel With**: —

**Blocks**: Task 3 (Messaging/connection features need discovery to find partners)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Geospatial indexing for user locations
- Search API with configurable radius
- Distance calculation and sorting
- Combined distance + compatibility scoring
- Efficient query patterns for scale

### What's NOT Included
- Real-time location tracking — privacy concerns, battery drain
- Complex matching algorithm — simple compatibility score first
- Caching layer — optimize after measuring actual load

---

## Prerequisites

Before starting:
- User profiles exist with latitude/longitude fields (Task 1)
- Database supports geospatial queries (PostGIS for Postgres, or MongoDB 2dsphere)
- Understanding of haversine formula for distance calculation

---

## Implementation Steps

### Step 1: Add Geospatial Index

**File**: `migrations/002_add_location_index.sql` (or equivalent)

**Purpose**: Enable efficient spatial queries without full table scans

PostGIS is the standard for Postgres. The index makes radius queries O(log n) instead of O(n).

**Pattern**:
```sql
-- Enable PostGIS extension (if not already)
CREATE EXTENSION IF NOT EXISTS postgis;

-- Add geometry column derived from lat/lng
ALTER TABLE users ADD COLUMN location geography(POINT, 4326);

-- Populate from existing lat/lng
UPDATE users SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Create spatial index
CREATE INDEX idx_users_location ON users USING GIST(location);

-- Trigger to keep location in sync
CREATE OR REPLACE FUNCTION update_user_location()
RETURNS TRIGGER AS $$
BEGIN
  NEW.location = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_location
BEFORE INSERT OR UPDATE OF latitude, longitude ON users
FOR EACH ROW EXECUTE FUNCTION update_user_location();
```

### Step 2: Create Discovery Query

**File**: `src/repositories/user.repository.ts`

**Purpose**: Encapsulate the geospatial query logic with distance calculation

The query finds users within radius, calculates exact distance, and returns sorted results. ST_DWithin uses the index; ST_Distance gives precise meters.

**Pattern**:
```typescript
interface DiscoveryParams {
  userId: string;
  latitude: number;
  longitude: number;
  radiusMeters: number;
  limit: number;
  offset: number;
}

interface DiscoveredPlayer {
  id: string;
  name: string;
  skillLevel: number;
  distanceMeters: number;
  compatibilityScore: number;
}

async function findNearbyPlayers(params: DiscoveryParams): Promise<DiscoveredPlayer[]> {
  const { userId, latitude, longitude, radiusMeters, limit, offset } = params;
  
  const query = `
    SELECT 
      u.id,
      u.name,
      u.skill_level,
      ST_Distance(
        u.location,
        ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography
      ) as distance_meters
    FROM users u
    WHERE u.id != $5
      AND u.is_active = true
      AND ST_DWithin(
        u.location,
        ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography,
        $3
      )
    ORDER BY distance_meters ASC
    LIMIT $4 OFFSET $6
  `;
  
  return db.query(query, [latitude, longitude, radiusMeters, limit, userId, offset]);
}
```

### Step 3: Implement Compatibility Scoring

**File**: `src/services/compatibility.service.ts`

**Purpose**: Calculate how well two players match based on skill level and availability

Start simple—skill level difference is the primary factor. Availability overlap can be added later. The score is 0-100 where higher is better.

**Pattern**:
```typescript
interface PlayerProfile {
  skillLevel: number;  // 1.0 to 7.0 (NTRP rating)
  playStyles: string[];
  availability: string[];  // e.g., ['weekday_morning', 'weekend_afternoon']
}

function calculateCompatibility(seeker: PlayerProfile, candidate: PlayerProfile): number {
  // Skill difference penalty: 0 diff = 100 points, 1.0 diff = 70 points, 2.0+ diff = 40 points
  const skillDiff = Math.abs(seeker.skillLevel - candidate.skillLevel);
  const skillScore = Math.max(40, 100 - (skillDiff * 30));
  
  // Availability overlap bonus (0-20 points)
  const availabilityOverlap = seeker.availability.filter(
    slot => candidate.availability.includes(slot)
  ).length;
  const availabilityScore = Math.min(20, availabilityOverlap * 5);
  
  // Play style match bonus (0-10 points)
  const styleOverlap = seeker.playStyles.filter(
    style => candidate.playStyles.includes(style)
  ).length;
  const styleScore = Math.min(10, styleOverlap * 5);
  
  return Math.round(skillScore + availabilityScore + styleScore);
}
```

### Step 4: Build Discovery API Endpoint

**File**: `src/controllers/discovery.controller.ts`

**Purpose**: Expose discovery as a REST endpoint with pagination

Combine distance query with compatibility scoring. Score calculation happens in application code to keep the SQL query simple and indexable.

**Pattern**:
```typescript
// GET /api/discovery?radius=10000&limit=20&offset=0

async function discoverPlayers(req: Request, res: Response) {
  const userId = req.user.id;
  const radius = Math.min(parseInt(req.query.radius) || 10000, 50000);  // Max 50km
  const limit = Math.min(parseInt(req.query.limit) || 20, 50);
  const offset = parseInt(req.query.offset) || 0;
  
  // Get seeker's profile for compatibility calculation
  const seeker = await userRepository.findById(userId);
  if (!seeker.latitude || !seeker.longitude) {
    return res.status(400).json({ error: 'Location required for discovery' });
  }
  
  // Find nearby players
  const nearby = await userRepository.findNearbyPlayers({
    userId,
    latitude: seeker.latitude,
    longitude: seeker.longitude,
    radiusMeters: radius,
    limit: limit + 10,  // Fetch extra to account for filtering
    offset
  });
  
  // Calculate compatibility and sort by combined score
  const results = nearby.map(player => ({
    ...player,
    compatibilityScore: calculateCompatibility(seeker, player),
    // Combined score: 70% compatibility, 30% proximity
    combinedScore: 0.7 * calculateCompatibility(seeker, player) + 
                   0.3 * (100 - Math.min(100, player.distanceMeters / radius * 100))
  }));
  
  // Sort by combined score, return limited results
  results.sort((a, b) => b.combinedScore - a.combinedScore);
  
  return res.json({
    players: results.slice(0, limit),
    hasMore: nearby.length > limit
  });
}
```

### Step 5: Add Discovery UI Component

**File**: `src/components/Discovery.tsx` (or equivalent mobile component)

**Purpose**: Display nearby players with distance and match quality indicators

Show distance in human-readable format. Highlight high compatibility matches. Enable tap to view full profile.

**Pattern**:
```typescript
function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${Math.round(meters)}m away`;
  }
  return `${(meters / 1000).toFixed(1)}km away`;
}

function CompatibilityBadge({ score }: { score: number }) {
  const level = score >= 80 ? 'great' : score >= 60 ? 'good' : 'fair';
  return <Badge variant={level}>{score}% match</Badge>;
}

function PlayerCard({ player }: { player: DiscoveredPlayer }) {
  return (
    <Card onClick={() => navigate(`/player/${player.id}`)}>
      <Avatar src={player.avatar} />
      <div>
        <h3>{player.name}</h3>
        <p>{player.skillLevel} NTRP · {formatDistance(player.distanceMeters)}</p>
      </div>
      <CompatibilityBadge score={player.compatibilityScore} />
    </Card>
  );
}
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Verify index exists and is used
psql -c "EXPLAIN ANALYZE SELECT * FROM users WHERE ST_DWithin(location, ST_MakePoint(-122.4, 37.7)::geography, 10000);"
# Should show "Index Scan using idx_users_location"

# 2. Test API endpoint
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3000/api/discovery?radius=5000&limit=10"

# 3. Verify distance calculation accuracy
# Create two test users with known coordinates, verify returned distance matches Google Maps
```

**Expected Result**: 
- Query uses spatial index (no Seq Scan)
- API returns players sorted by combined score
- Distance values accurate within 1%
- Response time < 100ms for 10k users in database

---

## Performance Considerations

| User Count | Expected Query Time | Notes |
|------------|---------------------|-------|
| 1,000 | < 10ms | Index handles easily |
| 100,000 | < 50ms | May need connection pooling |
| 1,000,000 | < 100ms | Consider read replicas |

If queries slow down:
1. Add `LIMIT` to ST_DWithin before distance calculation
2. Cache frequent searchers' results for 5 minutes
3. Partition users table by geographic region

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 2 complete
2. Proceed to Task 3 (Messaging/Connection)
3. Monitor query performance in production logs

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for geospatial approach
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking