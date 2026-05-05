# 🛠️ Task 3: Availability Matching

**Purpose**: Enable players to define when they're free to play and discover partners with overlapping schedules, solving the core coordination problem of tennis.

**Effort**: 3 days

**Dependencies**: Task 1 (Profile Creation) must be complete — availability attaches to player profiles

**Parallel With**: Task 2 (Location-based discovery) — availability and location are orthogonal filters

**Blocks**: Task 4 (Match recommendations) — availability overlap is a key ranking signal

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Recurring availability schema (weekly patterns)
- One-time availability entries (specific date/time slots)
- Availability overlap calculation algorithm
- UI for setting and editing availability
- Integration with player discovery results

### What's NOT Included
- Calendar sync (Google/Apple) — future enhancement, adds complexity
- Timezone conversion — MVP assumes local timezone only
- Availability forecasting — out of scope for initial release

---

## Prerequisites

Before starting:
- Player profile model exists with unique ID
- Basic CRUD API pattern established
- Date/time library selected (recommend date-fns or Luxon)

---

## Implementation Steps

### Step 1: Define Availability Schema

**File**: `src/models/availability.ts`

**Purpose**: Create data structures for both recurring and one-time availability

Recurring availability uses a weekly pattern with day-of-week and time ranges. One-time slots are specific datetime windows. Both share a common time range structure.

**Pattern**:
```typescript
interface TimeRange {
  start: string; // "18:00" (24h format)
  end: string;   // "21:00"
}

interface RecurringAvailability {
  id: string;
  playerId: string;
  dayOfWeek: 0 | 1 | 2 | 3 | 4 | 5 | 6; // 0 = Sunday
  timeRange: TimeRange;
  label?: string; // "Weekday evenings"
}

interface OneTimeAvailability {
  id: string;
  playerId: string;
  date: string;      // "2024-03-15" (ISO date)
  timeRange: TimeRange;
  expires: boolean;  // Auto-delete after date passes
}
```

### Step 2: Build Availability Storage

**File**: `src/services/availability.service.ts`

**Purpose**: CRUD operations for availability entries

Keep recurring and one-time availability in separate collections for simpler queries. Add automatic cleanup of expired one-time slots.

**Pattern**:
```typescript
class AvailabilityService {
  // Recurring
  async setRecurring(playerId: string, slots: RecurringAvailability[]): Promise<void>
  async getRecurring(playerId: string): Promise<RecurringAvailability[]>
  
  // One-time
  async addOneTime(playerId: string, slot: OneTimeAvailability): Promise<string>
  async removeOneTime(slotId: string): Promise<void>
  async getUpcomingOneTime(playerId: string, days?: number): Promise<OneTimeAvailability[]>
  
  // Cleanup (run daily via cron)
  async purgeExpiredSlots(): Promise<number>
}
```

### Step 3: Implement Overlap Algorithm

**File**: `src/services/availability-matcher.ts`

**Purpose**: Calculate whether two players have overlapping free time

The algorithm checks both recurring and one-time availability. For recurring, it finds shared days and intersecting time ranges. For one-time, it looks for exact date matches with time overlap.

**Pattern**:
```typescript
interface OverlapResult {
  hasOverlap: boolean;
  recurringMatches: Array<{
    dayOfWeek: number;
    sharedWindow: TimeRange;
  }>;
  oneTimeMatches: Array<{
    date: string;
    sharedWindow: TimeRange;
  }>;
  overlapScore: number; // 0-100, for ranking
}

function calculateOverlap(
  seekerAvailability: { recurring: RecurringAvailability[], oneTime: OneTimeAvailability[] },
  candidateAvailability: { recurring: RecurringAvailability[], oneTime: OneTimeAvailability[] }
): OverlapResult {
  // 1. Group recurring by day
  // 2. For matching days, find time range intersection
  // 3. Check one-time slots for date + time overlap
  // 4. Calculate score: more overlap hours = higher score
}

function intersectTimeRanges(a: TimeRange, b: TimeRange): TimeRange | null {
  const start = max(a.start, b.start);
  const end = min(a.end, b.end);
  return start < end ? { start, end } : null;
}
```

### Step 4: Build Availability UI Component

**File**: `src/components/AvailabilityEditor.tsx`

**Purpose**: Visual weekly grid for setting recurring availability

Use a 7-column grid (days) with time slots as rows. Tap to toggle availability. Show existing one-time slots in a separate list below.

**Pattern**:
```tsx
function AvailabilityEditor({ playerId, onSave }) {
  const [recurring, setRecurring] = useState<RecurringAvailability[]>([]);
  const [oneTime, setOneTime] = useState<OneTimeAvailability[]>([]);
  
  // Visual grid: 7 columns (Sun-Sat), rows for time blocks
  // Preset buttons: "Weekday evenings", "Weekend mornings"
  // One-time: date picker + time range selector
  
  return (
    <div>
      <WeeklyGrid slots={recurring} onToggle={handleToggle} />
      <PresetButtons onSelect={applyPreset} />
      <Divider />
      <OneTimeList slots={oneTime} onAdd={addOneTime} onRemove={removeOneTime} />
    </div>
  );
}
```

### Step 5: Integrate with Discovery

**File**: `src/services/discovery.service.ts`

**Purpose**: Add availability filtering to player search results

When a player searches for partners, fetch their availability and filter/rank candidates by overlap score. This combines with location proximity from Task 2.

**Pattern**:
```typescript
async function discoverPlayers(seekerId: string, filters: DiscoveryFilters): Promise<PlayerMatch[]> {
  const seekerAvailability = await availabilityService.getAll(seekerId);
  
  // Get candidates (from location filter, Task 2)
  const candidates = await getCandidatesByLocation(seekerId, filters.radius);
  
  // Score each by availability overlap
  const scored = await Promise.all(candidates.map(async (candidate) => {
    const candidateAvailability = await availabilityService.getAll(candidate.id);
    const overlap = calculateOverlap(seekerAvailability, candidateAvailability);
    
    return {
      ...candidate,
      availabilityOverlap: overlap,
      // Combined score: location weight + availability weight
      matchScore: computeMatchScore(candidate.distance, overlap.overlapScore)
    };
  }));
  
  // Filter out zero overlap if filter enabled
  const filtered = filters.requireOverlap 
    ? scored.filter(p => p.availabilityOverlap.hasOverlap)
    : scored;
  
  return filtered.sort((a, b) => b.matchScore - a.matchScore);
}
```

### Step 6: Display Overlap in Results

**File**: `src/components/PlayerCard.tsx`

**Purpose**: Show availability match quality in search results

Display a visual indicator of schedule compatibility. "Great match: 3 overlapping times" is more actionable than a percentage.

**Pattern**:
```tsx
function AvailabilityBadge({ overlap }: { overlap: OverlapResult }) {
  if (!overlap.hasOverlap) {
    return <Badge variant="muted">No schedule overlap</Badge>;
  }
  
  const totalSlots = overlap.recurringMatches.length + overlap.oneTimeMatches.length;
  
  // Summarize: "Tue/Thu evenings" or "This Saturday"
  const summary = formatOverlapSummary(overlap);
  
  return (
    <Badge variant="success">
      {totalSlots} matching time{totalSlots > 1 ? 's' : ''}: {summary}
    </Badge>
  );
}
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Create two test players with overlapping availability
curl -X POST /api/players/player-1/availability/recurring \
  -d '{"dayOfWeek": 2, "timeRange": {"start": "18:00", "end": "21:00"}}'

curl -X POST /api/players/player-2/availability/recurring \
  -d '{"dayOfWeek": 2, "timeRange": {"start": "19:00", "end": "22:00"}}'

# 2. Check overlap calculation
curl /api/availability/overlap?seeker=player-1&candidate=player-2

# Expected: overlap on Tuesday 19:00-21:00

# 3. Verify discovery integration
curl /api/discover?playerId=player-1&requireOverlap=true

# Player-2 should appear with availability badge
```

**Expected Result**: 
- Players can set weekly recurring availability
- Players can add one-time "I'm free Thursday" slots
- Discovery shows candidates sorted by schedule overlap
- UI clearly indicates shared available times

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 3 complete
2. Proceed to Task 4 (Match recommendations) which uses overlap scores
3. Consider adding "Suggest a time" feature in messaging (future)

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for availability model
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking